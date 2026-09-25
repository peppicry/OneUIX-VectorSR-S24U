#!/usr/bin/env python3
from pathlib import Path

NETWORK = Path("hook/src/main/java/io/github/soclear/oneuix/hook/Network.kt")
BUILD = Path("app/build.gradle.kts")

text = NETWORK.read_text(encoding="utf-8")

# Add imports used by the One UI 8.5 fallback preference injection.
text = text.replace(
    "import android.graphics.Typeface\n",
    "import android.content.Context\nimport android.graphics.Typeface\nimport android.os.Bundle\nimport android.provider.Settings as AndroidSettings\nimport java.lang.reflect.Proxy\n",
    1,
)

old = '''    context(xposedModule: XposedModule, param: XposedModuleInterface.PackageReadyParam)
    fun supportRealTimeNetworkSpeed() {
        if (param.packageName != Package.SETTINGS &&
            param.packageName != Package.SYSTEMUI
        ) {
            return
        }
        try {
            val semCscFeatureClass =
                param.classLoader.loadClass("com.samsung.android.feature.SemCscFeature")
            val method = semCscFeatureClass.getDeclaredMethod(
                "getBoolean",
                String::class.java,
                Boolean::class.javaPrimitiveType
            )
            xposedModule.hook(method).intercept { chain ->
                if (chain.args.firstOrNull() == "CscFeature_Common_SupportZProjectFunctionInGlobal") {
                    true
                } else {
                    chain.proceed()
                }
            }
        } catch (t: Throwable) {
            xlog(t)
        }
    }
'''

new = '''    context(xposedModule: XposedModule, param: XposedModuleInterface.PackageReadyParam)
    fun supportRealTimeNetworkSpeed() {
        if (param.packageName != Package.SETTINGS &&
            param.packageName != Package.SYSTEMUI
        ) {
            return
        }

        val networkSpeedFeatureKeys = setOf(
            "CscFeature_Common_SupportZProjectFunctionInGlobal",
            "CscFeature_Setting_SupportRealTimeNetworkSpeed",
        )

        // Keep both Samsung CSC gates enabled in Settings and SystemUI.
        try {
            val semCscFeatureClass =
                param.classLoader.loadClass("com.samsung.android.feature.SemCscFeature")
            semCscFeatureClass.declaredMethods
                .filter { method ->
                    method.name == "getBoolean" &&
                        method.parameterTypes.firstOrNull() == String::class.java
                }
                .forEach { method ->
                    xposedModule.hook(method).intercept { chain ->
                        val featureName = chain.args.firstOrNull() as? String
                        if (featureName in networkSpeedFeatureKeys) {
                            true
                        } else {
                            chain.proceed()
                        }
                    }
                }
            xlog("[OneUIX-VectorSR] network-speed CSC hooks active in ${param.packageName}")
        } catch (t: Throwable) {
            xlog(t)
        }

        if (param.packageName == Package.SETTINGS) {
            // Force Samsung's controller to expose the preference when the firmware
            // caches feature support before the CSC hook becomes observable.
            try {
                val controllerClass = param.classLoader.loadClass(
                    "com.samsung.android.settings.notification.StatusBarNetworkSpeedController"
                )
                val availabilityMethod = controllerClass.getDeclaredMethod("getAvailabilityStatus")
                xposedModule.hook(availabilityMethod).intercept {
                    0
                }
                xlog(
                    "[OneUIX-VectorSR] StatusBarNetworkSpeedController availability forced to AVAILABLE"
                )
            } catch (t: Throwable) {
                xlog(t)
            }

            // One UI 8.5 on the tested S24 Ultra can omit the network_speed
            // preference from Advanced notification settings. Inject a
            // SwitchPreferenceCompat and bind it to Samsung's Settings.System key.
            try {
                val fragmentClass = param.classLoader.loadClass(
                    "com.samsung.android.settings.notification.ConfigureNotificationMoreSettings"
                )
                val onCreateMethod = fragmentClass.getDeclaredMethod(
                    "onCreate",
                    Bundle::class.java,
                )
                xposedModule.hook(onCreateMethod).intercept { chain ->
                    val result = chain.proceed()
                    try {
                        val fragment = chain.thisObject
                        val preferenceScreen =
                            fragment.reflect.call("getPreferenceScreen") ?: return@intercept result

                        val existing = preferenceScreen.reflect.call(
                            "findPreference",
                            "network_speed",
                        )
                        if (existing != null) {
                            xlog("[OneUIX-VectorSR] native network_speed preference already present")
                            return@intercept result
                        }

                        val context = fragment.reflect.call("requireContext") as Context
                        val switchClass = param.classLoader.loadClass(
                            "androidx.preference.SwitchPreferenceCompat"
                        )
                        val preference = switchClass
                            .getConstructor(Context::class.java)
                            .newInstance(context)

                        preference.reflect.call("setKey", "network_speed")
                        preference.reflect.call("setPersistent", false)

                        val titleResId = context.resources.getIdentifier(
                            "real_time_network_speed_title",
                            "string",
                            Package.SETTINGS,
                        )
                        val title = if (titleResId != 0) {
                            context.getString(titleResId)
                        } else {
                            "Mostrar velocidade da rede em tempo real"
                        }
                        preference.reflect.call("setTitle", title)

                        val enabled = AndroidSettings.System.getInt(
                            context.contentResolver,
                            "network_speed",
                            0,
                        ) != 0
                        preference.reflect.call("setChecked", enabled)

                        val listenerClass = param.classLoader.loadClass(
                            "androidx.preference.Preference\$OnPreferenceChangeListener"
                        )
                        val listener = Proxy.newProxyInstance(
                            param.classLoader,
                            arrayOf(listenerClass),
                        ) { proxy, method, args ->
                            when (method.name) {
                                "onPreferenceChange" -> {
                                    val newValue = args?.getOrNull(1) as? Boolean
                                        ?: return@newProxyInstance false
                                    AndroidSettings.System.putInt(
                                        context.contentResolver,
                                        "network_speed",
                                        if (newValue) 1 else 0,
                                    )
                                    true
                                }

                                "toString" -> "OneUIXNetworkSpeedListener"
                                "hashCode" -> System.identityHashCode(proxy)
                                "equals" -> proxy === args?.getOrNull(0)
                                else -> null
                            }
                        }
                        preference.reflect.call("setOnPreferenceChangeListener", listener)

                        val anchor = preferenceScreen.reflect.call(
                            "findPreference",
                            "show_notification_app_icon",
                        )
                        if (anchor != null) {
                            val anchorOrder = anchor.reflect.call("getOrder") as? Int
                            if (anchorOrder != null && anchorOrder < Int.MAX_VALUE) {
                                preference.reflect.call("setOrder", anchorOrder + 1)
                            }
                        }

                        preferenceScreen.reflect.call("addPreference", preference)
                        xlog(
                            "[OneUIX-VectorSR] injected network_speed preference into ConfigureNotificationMoreSettings"
                        )
                    } catch (t: Throwable) {
                        xlog(t)
                    }
                    result
                }
                xlog("[OneUIX-VectorSR] advanced-settings network_speed injector armed")
            } catch (t: Throwable) {
                xlog(t)
            }
        }
    }
'''

if old not in text:
    raise SystemExit("Network.kt supportRealTimeNetworkSpeed anchor not found; upstream changed")
text = text.replace(old, new, 1)

# Convert the existing separate upload/download formatter from bytes/s to SI bits/s.
old_format = '''        // 格式化网速，speed 为每秒字节数
        fun formatSpeed(bytesPerSecond: Float): String {
            // 0 或负数显示为 "0B"
            if (bytesPerSecond <= 0f) {
                return "0B"
            }
            if (bytesPerSecond < 1024f) {
                return "${bytesPerSecond.roundToInt()}B"
            }
            val kiBytesPerSecond = bytesPerSecond / 1024f
            if (kiBytesPerSecond < 100f) {
                return "%.2fK".format(kiBytesPerSecond)
            }
            if (kiBytesPerSecond < 1000f) {
                return "%.1fK".format(kiBytesPerSecond)
            }
            val miBytesPerSecond = kiBytesPerSecond / 1024f
            if (miBytesPerSecond < 100f) {
                return "%.2fM".format(miBytesPerSecond)
            }
            return "%.1fM".format(miBytesPerSecond)
        }
'''
new_format = '''        // Format real-time speed in bits/second (compact status-bar notation).
        // TrafficStats reports bytes; multiply by 8 and use decimal SI units.
        fun formatSpeed(bytesPerSecond: Float): String {
            if (bytesPerSecond <= 0f) {
                return "0b"
            }

            val bitsPerSecond = bytesPerSecond * 8f
            if (bitsPerSecond < 1000f) {
                return "${bitsPerSecond.roundToInt()}b"
            }

            val kiloBitsPerSecond = bitsPerSecond / 1000f
            if (kiloBitsPerSecond < 100f) {
                return "%.2fKb".format(kiloBitsPerSecond)
            }
            if (kiloBitsPerSecond < 1000f) {
                return "%.1fKb".format(kiloBitsPerSecond)
            }

            val megaBitsPerSecond = kiloBitsPerSecond / 1000f
            if (megaBitsPerSecond < 100f) {
                return "%.2fMb".format(megaBitsPerSecond)
            }
            if (megaBitsPerSecond < 1000f) {
                return "%.1fMb".format(megaBitsPerSecond)
            }

            val gigaBitsPerSecond = megaBitsPerSecond / 1000f
            if (gigaBitsPerSecond < 100f) {
                return "%.2fGb".format(gigaBitsPerSecond)
            }
            return "%.1fGb".format(gigaBitsPerSecond)
        }
'''
if old_format not in text:
    raise SystemExit("Network.kt formatSpeed anchor not found; upstream changed")
text = text.replace(old_format, new_format, 1)

old_interval = "        intervalMillisecond: Long = 3000L,\n"
new_interval = "        intervalMillisecond: Long = 1000L,\n"
if old_interval not in text:
    raise SystemExit("Network.kt interval anchor not found; upstream changed")
NETWORK.write_text(text.replace(old_interval, new_interval, 1), encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")
old_version = 'versionName = "1.9.0"'
new_version = 'versionName = "1.9.0-vectorsr-s24u"'
if old_version not in build:
    raise SystemExit("One UI X versionName anchor not found; upstream changed")
BUILD.write_text(build.replace(old_version, new_version, 1), encoding="utf-8")

print("Applied One UI X 1.9.0 Vector-SR/S24U network-speed compatibility patch")
