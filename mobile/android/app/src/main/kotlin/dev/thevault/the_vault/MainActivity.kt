package dev.thevault.the_vault

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Handler
import android.os.Looper
import java.net.Inet4Address
import java.util.ArrayDeque

class MainActivity : FlutterActivity() {
    private val handler = Handler(Looper.getMainLooper())
    private val nsd by lazy { getSystemService(NSD_SERVICE) as NsdManager }
    private var pending: MethodChannel.Result? = null
    private var listener: NsdManager.DiscoveryListener? = null
    private val found = linkedMapOf<String, Map<String, Any>>()
    private val queue = ArrayDeque<NsdServiceInfo>()
    private var resolving = false
    private var generation = 0

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "dev.thevault/discovery")
            .setMethodCallHandler { call, result ->
                if (call.method != "discover") result.notImplemented()
                else if (pending != null) result.error("busy", "Discovery is already running", null)
                else discover(result)
            }
    }

    @Suppress("DEPRECATION")
    private fun discover(result: MethodChannel.Result) {
        pending = result
        generation++
        val current = generation
        found.clear()
        queue.clear()
        resolving = false
        listener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(type: String) {}
            override fun onDiscoveryStopped(type: String) {}
            override fun onStopDiscoveryFailed(type: String, code: Int) {}
            override fun onStartDiscoveryFailed(type: String, code: Int) {
                handler.post { if (current == generation) completeDiscovery("Local discovery could not start. Check Wi-Fi.") }
            }
            override fun onServiceLost(info: NsdServiceInfo) {}
            override fun onServiceFound(info: NsdServiceInfo) {
                if (info.serviceType.trimEnd('.') != "_thevault._tcp") return
                handler.post {
                    if (current == generation && pending != null) {
                        queue.add(info)
                        resolveNext(current)
                    }
                }
            }
        }
        try {
            nsd.discoverServices("_thevault._tcp.", NsdManager.PROTOCOL_DNS_SD, listener)
            handler.postDelayed({ if (current == generation) completeDiscovery() }, 8000)
        } catch (e: Exception) {
            completeDiscovery("Local discovery is unavailable. Check network permissions.")
        }
    }

    @Suppress("DEPRECATION")
    private fun resolveNext(current: Int) {
        if (current != generation || pending == null || resolving || queue.isEmpty()) return
        resolving = true
        nsd.resolveService(queue.removeFirst(), object : NsdManager.ResolveListener {
            override fun onResolveFailed(info: NsdServiceInfo, code: Int) {
                handler.post {
                    if (current == generation) { resolving = false; resolveNext(current) }
                }
            }
            override fun onServiceResolved(info: NsdServiceInfo) {
                handler.post {
                    if (current != generation || pending == null) return@post
                    if (info.host is Inet4Address) {
                        val attributes = info.attributes.mapValues { String(it.value, Charsets.UTF_8) }
                        val id = attributes["id"]
                        val fingerprint = attributes["sha256"]
                        val host = info.host?.hostAddress
                        if (id != null && fingerprint != null && host != null) {
                            found[id] = mapOf("id" to id, "name" to (attributes["name"] ?: info.serviceName),
                                "sha256" to fingerprint, "host" to host, "port" to info.port)
                        }
                    }
                    resolving = false
                    resolveNext(current)
                }
            }
        })
    }

    // Do not name this finish: Activity.finish() wins overload resolution for
    // a no-argument call and closes the app when the discovery timer expires.
    private fun completeDiscovery(error: String? = null) {
        val result = pending ?: return
        pending = null
        generation++
        listener?.let { try { nsd.stopServiceDiscovery(it) } catch (_: Exception) {} }
        listener = null
        queue.clear()
        if (error == null) result.success(found.values.toList())
        else result.error("discovery", error, null)
    }

    override fun onDestroy() {
        completeDiscovery("Discovery stopped")
        super.onDestroy()
    }
}
