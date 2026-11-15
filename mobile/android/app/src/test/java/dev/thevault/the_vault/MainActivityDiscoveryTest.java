package dev.thevault.the_vault;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.robolectric.Shadows.shadowOf;

import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.os.Looper;
import io.flutter.plugin.common.MethodChannel;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.net.InetAddress;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import kotlin.LazyKt;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.LooperMode;

/** Exercises the real activity's discovery callbacks without starting a Flutter engine. */
@RunWith(RobolectricTestRunner.class)
@Config(manifest = Config.NONE, sdk = 34)
@LooperMode(LooperMode.Mode.PAUSED)
public class MainActivityDiscoveryTest {
    private MainActivity activity;
    private NsdManager nsd;
    private NsdManager.DiscoveryListener discoveryListener;

    @Before
    public void setUp() throws Exception {
        activity = new MainActivity();
        nsd = mock(NsdManager.class);
        Field service = MainActivity.class.getDeclaredField("nsd$delegate");
        service.setAccessible(true);
        service.set(activity, LazyKt.lazy(() -> nsd));
        doAnswer(invocation -> {
            discoveryListener = invocation.getArgument(2);
            return null;
        }).when(nsd).discoverServices(anyString(), anyInt(), any(NsdManager.DiscoveryListener.class));
    }

    private Reply discover() throws Exception {
        Reply reply = new Reply();
        Method method = MainActivity.class.getDeclaredMethod("discover", MethodChannel.Result.class);
        method.setAccessible(true);
        method.invoke(activity, reply);
        return reply;
    }

    @Test
    public void emptyDiscoveryCompletesWithoutClosingTheActivity() throws Exception {
        Reply reply = discover();
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(7));
        assertEquals(0, reply.calls);
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(2));

        assertFalse("Discovery must never call Activity.finish()", activity.isFinishing());
        assertEquals(1, reply.calls);
        assertNull(reply.error);
        assertEquals(List.of(), reply.value);
        verify(nsd).stopServiceDiscovery(discoveryListener);
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(30));
        assertEquals("Reply must be delivered exactly once", 1, reply.calls);
    }

    @Test
    public void resolvedComputerIsReturnedWhenTheTimerExpires() throws Exception {
        Reply reply = discover();
        NsdServiceInfo server = new NsdServiceInfo();
        server.setServiceName("THE VAULT test");
        server.setServiceType("_thevault._tcp.");
        server.setHost(InetAddress.getByName("192.168.1.20"));
        server.setPort(8443);
        server.setAttribute("id", "12345678-1234-1234-1234-123456789abc");
        server.setAttribute("name", "My computer");
        server.setAttribute("sha256", "a".repeat(64));
        discoveryListener.onServiceFound(server);
        shadowOf(Looper.getMainLooper()).idle();
        ArgumentCaptor<NsdManager.ResolveListener> resolver = ArgumentCaptor.forClass(NsdManager.ResolveListener.class);
        verify(nsd).resolveService(eq(server), resolver.capture());
        resolver.getValue().onServiceResolved(server);
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(9));

        assertFalse(activity.isFinishing());
        assertEquals(1, reply.calls);
        assertNull(reply.error);
        List<?> servers = (List<?>) reply.value;
        assertEquals(1, servers.size());
        Map<?, ?> record = (Map<?, ?>) servers.get(0);
        assertEquals("My computer", record.get("name"));
        assertEquals("192.168.1.20", record.get("host"));
        assertEquals(8443, record.get("port"));
        assertEquals("a".repeat(64), record.get("sha256"));
    }

    @Test
    public void discoveryCanRunAgainAfterItsFirstTimeout() throws Exception {
        Reply first = discover();
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(9));
        Reply second = discover();
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(9));
        assertFalse(activity.isFinishing());
        assertEquals(1, first.calls);
        assertEquals(1, second.calls);
        assertEquals(List.of(), second.value);
    }

    @Test
    public void startFailureReportsAnErrorWithoutClosingTheActivity() throws Exception {
        Reply reply = discover();
        discoveryListener.onStartDiscoveryFailed("_thevault._tcp.", NsdManager.FAILURE_INTERNAL_ERROR);
        shadowOf(Looper.getMainLooper()).idleFor(Duration.ofSeconds(9));
        assertFalse(activity.isFinishing());
        assertEquals(1, reply.calls);
        assertEquals("discovery", reply.error);
    }

    private static final class Reply implements MethodChannel.Result {
        int calls;
        Object value;
        String error;
        @Override public void success(Object value) { calls++; this.value = value; }
        @Override public void error(String code, String message, Object details) { calls++; error = code; }
        @Override public void notImplemented() { fail("Discovery must be implemented"); }
    }
}
