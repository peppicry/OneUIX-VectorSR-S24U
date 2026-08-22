#!/usr/bin/env python3
from pathlib import Path

NETWORK = Path("app/src/main/java/io/github/soclear/oneuix/hook/Network.kt")
BUILD = Path("app/build.gradle.kts")

text = NETWORK.read_text(encoding="utf-8")

# Add imports used by the One UI 8.5 fallback preference injection.
text = text.replace(
    "import android.graphics.Typeface\n",
    "import android.content.Context\nimport android.graphics.Typeface\nimport android.os.Bundle\nimport android.provider.Settings as AndroidSettings\nimport java.lang.reflect.Proxy\n",
    1,
)

old = '''    fun supportRealTimeNetworkSpeed(loadPackageParam: LoadPackageParam) {
        if (loadPackageParam.packageName != Package.SETTINGS &&
            loadPackageParam.packageName != Package.SYSTEMUI
        ) {
            return
        }
        try {
            findAndHookMethod(
                "com.samsung.android.feature.SemCscFeature",
                loadPackageParam.classLoader,
                "getBoolean",
                String::class.java,
                Boolean::class.java,
                object : XC_MethodHook() {
                    override fun beforeHookedMethod(param: MethodHookParam) {
                        if (param.args[0] == "CscFeature_Common_SupportZProjectFunctionInGlobal") {
                            param.result = true
                        }
                    }
                }
            )
        } catch (t: Throwable) {
            XposedBridge.log(t)
        }
    }
'''

new = '''    fun supportRealTimeNetworkSpeed(loadPackageParam: LoadPackageParam) {
        if (loadPackageParam.packageName != Package.SETTINGS &&
            loadPackageParam.packageName != Package.SYSTEMUI
        ) {
            return
        }

        val networkSpeedFeatureKeys = setOf(
            "CscFeature_Common_SupportZProjectFunctionInGlobal",
            "CscFeature_Setting_SupportRealTimeNetworkSpeed",
        )

        // Keep both Samsung CSC gates enabled in Settings and SystemUI.
        try {
            val semCscFeatureClass = findClass(
                "com.samsung.android.feature.SemCscFeature",
                loadPackageParam.classLoader,
            )
            XposedBridge.hookAllMethods(
                semCscFeatureClass,
                "getBoolean",
                object : XC_MethodHook() {
                    override fun beforeHookedMethod(param: MethodHookParam) {
                        val featureName = param.args.firstOrNull() as? String ?: return
                        if (featureName in networkSpeedFeatureKeys) {
                            param.result = true
                        }
                    }
                }
            )
            XposedBridge.log(
                "[OneUIX-VectorSR] network-speed CSC hooks active in ${loadPackageParam.packageName}"
            )
        } catch (t: Throwable) {
            XposedBridge.log(t)
        }

        if (loadPackageParam.packageName == Package.SETTINGS) {
            // Older/newer Samsung Settings builds can cache support before the CSC hook
            // becomes observable. Force the controller itself to report AVAILABLE.
            try {
                findAndHookMethod(
                    "com.samsung.android.settings.notification.StatusBarNetworkSpeedController",
                    loadPackageParam.classLoader,
                    "getAvailabilityStatus",
                    object : XC_MethodHook() {
                        override fun beforeHookedMethod(param: MethodHookParam) {
                            param.result = 0
                        }
                    }
                )
                XposedBridge.log(
                    "[OneUIX-VectorSR] StatusBarNetworkSpeedController availability forced to AVAILABLE"
                )
            } catch (t: Throwable) {
                XposedBridge.log(t)
            }

            // One UI 8.5 on the tested S24 Ultra no longer exposes the network_speed
            // preference in sec_configure_notification_more_settings.xml. Inject a
            // SwitchPreferenceCompat directly into that screen and bind it to the same
            // Settings.System key already consumed by Samsung SystemUI.
            try {
                findAndHookMethod(
                    "com.samsung.android.settings.notification.ConfigureNotificationMoreSettings",
                    loadPackageParam.classLoader,
                    "onCreate",
                    Bundle::class.java,
                    object : XC_MethodHook() {
                        override fun afterHookedMethod(param: MethodHookParam) {
                            try {
                                val fragment = param.thisObject
                                val preferenceScreen = callMethod(fragment, "getPreferenceScreen") ?: return

                                // Do not create a duplicate if Samsung restores the preference later.
                                val existing = callMethod(
                                    preferenceScreen,
                                    "findPreference",
                                    "network_speed",
                                )
                                if (existing != null) {
                                    XposedBridge.log(
                                        "[OneUIX-VectorSR] native network_speed preference already present"
                                    )
                                    return
                                }

                                val context = callMethod(fragment, "requireContext") as Context
                                val switchClass = findClass(
                                    "androidx.preference.SwitchPreferenceCompat",
                                    loadPackageParam.classLoader,
                                )
                                val preference = switchClass
                                    .getConstructor(Context::class.java)
                                    .newInstance(context)

                                callMethod(preference, "setKey", "network_speed")
                                callMethod(preference, "setPersistent", false)

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
                                callMethod(preference, "setTitle", title)

                                val enabled = AndroidSettings.System.getInt(
                                    context.contentResolver,
                                    "network_speed",
                                    0,
                                ) != 0
                                callMethod(preference, "setChecked", enabled)

                                val listenerClass = findClass(
                                    "androidx.preference.Preference\\$OnPreferenceChangeListener",
                                    loadPackageParam.classLoader,
                                )
                                val listener = Proxy.newProxyInstance(
                                    loadPackageParam.classLoader,
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
                                callMethod(preference, "setOnPreferenceChangeListener", listener)

                                // Keep it close to Samsung's existing status-bar notification toggle.
                                val anchor = callMethod(
                                    preferenceScreen,
                                    "findPreference",
                                    "show_notification_app_icon",
                                )
                                if (anchor != null) {
                                    val anchorOrder = callMethod(anchor, "getOrder") as? Int
                                    if (anchorOrder != null && anchorOrder < Int.MAX_VALUE) {
                                        callMethod(preference, "setOrder", anchorOrder + 1)
                                    }
                                }

                                callMethod(preferenceScreen, "addPreference", preference)
                                XposedBridge.log(
                                    "[OneUIX-VectorSR] injected network_speed preference into ConfigureNotificationMoreSettings"
                                )
                            } catch (t: Throwable) {
                                XposedBridge.log(t)
                            }
                        }
                    }
                )
                XposedBridge.log(
                    "[OneUIX-VectorSR] advanced-settings network_speed injector armed"
                )
            } catch (t: Throwable) {
                XposedBridge.log(t)
            }
        }
    }
'''

if old not in text:
    raise SystemExit("Network.kt supportRealTimeNetworkSpeed anchor not found; upstream changed")
NETWORK.write_text(text.replace(old, new, 1), encoding="utf-8")

# Convert the existing separate upload/download formatter from bytes/s to SI bits/s.
old_format = '            // 格式化网速，speed 为每秒字节数\n            private fun formatSpeed(bytesPerSecond: Float): String {\n                // 0 或负数显示为 "0B"\n                if (bytesPerSecond <= 0f) {\n                    return "0B"\n                }\n                if (bytesPerSecond < 1024f) {\n                    return "${bytesPerSecond.roundToInt()}B"\n                }\n                val kiBytesPerSecond = bytesPerSecond / 1024f\n                if (kiBytesPerSecond < 100f) {\n                    return "%.2fK".format(kiBytesPerSecond)\n                }\n                if (kiBytesPerSecond < 1000f) {\n                    return "%.1fK".format(kiBytesPerSecond)\n                }\n                val miBytesPerSecond = kiBytesPerSecond / 1024f\n                if (miBytesPerSecond < 100f) {\n                    return "%.2fM".format(miBytesPerSecond)\n                }\n                return "%.1fM".format(miBytesPerSecond)\n            }\n'
new_format = '            // Format real-time speed in bits/second (compact status-bar notation).\n            // TrafficStats reports bytes; multiply by 8 and use decimal SI units.\n            private fun formatSpeed(bytesPerSecond: Float): String {\n                if (bytesPerSecond <= 0f) {\n                    return "0b"\n                }\n\n                val bitsPerSecond = bytesPerSecond * 8f\n                if (bitsPerSecond < 1000f) {\n                    return "${bitsPerSecond.roundToInt()}b"\n                }\n\n                val kiloBitsPerSecond = bitsPerSecond / 1000f\n                if (kiloBitsPerSecond < 100f) {\n                    return "%.2fKb".format(kiloBitsPerSecond)\n                }\n                if (kiloBitsPerSecond < 1000f) {\n                    return "%.1fKb".format(kiloBitsPerSecond)\n                }\n\n                val megaBitsPerSecond = kiloBitsPerSecond / 1000f\n                if (megaBitsPerSecond < 100f) {\n                    return "%.2fMb".format(megaBitsPerSecond)\n                }\n                if (megaBitsPerSecond < 1000f) {\n                    return "%.1fMb".format(megaBitsPerSecond)\n                }\n\n                val gigaBitsPerSecond = megaBitsPerSecond / 1000f\n                if (gigaBitsPerSecond < 100f) {\n                    return "%.2fGb".format(gigaBitsPerSecond)\n                }\n                return "%.1fGb".format(gigaBitsPerSecond)\n            }\n'
if old_format not in text:
    raise SystemExit("Network.kt formatSpeed anchor not found; upstream changed")
NETWORK.write_text(text.replace(old_format, new_format, 1), encoding="utf-8")

# Refresh separate upload/download network speed every second instead of every 3 seconds.
text = NETWORK.read_text(encoding="utf-8")
old_interval = "        intervalMillisecond: Long = 3000L\n"
new_interval = "        intervalMillisecond: Long = 1000L\n"
if old_interval not in text:
    raise SystemExit("Network.kt interval anchor not found; upstream changed")
NETWORK.write_text(text.replace(old_interval, new_interval, 1), encoding="utf-8")

build = BUILD.read_text(encoding="utf-8")
old_version = 'versionName = "1.7.0"'
new_version = 'versionName = "1.7.0-vectorsr-s24u"'
if old_version not in build:
    raise SystemExit("One UI X versionName anchor not found; upstream changed")
BUILD.write_text(build.replace(old_version, new_version, 1), encoding="utf-8")

print("Applied One UI X Vector-SR/S24U network-speed compatibility patch")
