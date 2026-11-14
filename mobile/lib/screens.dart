import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';
import 'design.dart';
import 'capture_screen.dart';
import 'network/discovery.dart';

class VaultHome extends StatefulWidget {
  final VaultApi api;
  final bool initialize;
  const VaultHome({super.key, required this.api, this.initialize = true});
  @override
  State<VaultHome> createState() => _VaultHomeState();
}

class _VaultHomeState extends State<VaultHome> {
  bool busy = false;
  Map<String, dynamic>? health;
  @override
  void initState() {
    super.initState();
    if (widget.initialize) _load();
  }

  Future<void> _load() async {
    try {
      await widget.api.initialize();
      health = await widget.api.request('GET', '/api/v1/health');
    } catch (_) {
      health = null;
    }
    if (mounted) setState(() {});
  }

  Future<void> _navigate(Widget screen) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
    if (mounted) setState(() {});
  }

  Future<void> _open() async {
    if (widget.api.profile == null && widget.api.managementToken == null) {
      await _navigate(ConsentScreen(api: widget.api));
      return;
    }
    setState(() => busy = true);
    try {
      await widget.api.refreshProfile();
      final p = widget.api.profile!;
      if ((p['sequence'] as List).any(
        (l) => !(p['enrolled'] as List).contains(l),
      )) {
        if (mounted) await _navigate(RitualScreen(api: widget.api));
      } else {
        final session = await widget.api.start('', false);
        if (!mounted) return;
        final unlocked = await Navigator.of(context).push<bool>(
          MaterialPageRoute(
            builder: (_) => CaptureScreen(
              api: widget.api,
              session: session,
              enrollment: false,
            ),
          ),
        );
        if (mounted && unlocked == true) {
          await _navigate(RevealScreen(api: widget.api));
        }
      }
    } catch (e) {
      if (mounted) showError(context, e);
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final profile = widget.api.profile;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: LayoutBuilder(
              builder: (context, constraints) => SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(28, 20, 28, 24),
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    minHeight: constraints.maxHeight - 44,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          GestureDetector(
                            onLongPress: () {
                              demoMode = !demoMode;
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    'Live diagnostics ${demoMode ? 'on' : 'off'}',
                                  ),
                                ),
                              );
                            },
                            child: const Row(
                              children: [
                                Glyph('vault', size: 28, color: lime),
                                SizedBox(width: 12),
                                Text(
                                  'THE VAULT',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 2,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const Spacer(),
                          IconButton(
                            tooltip: 'Settings',
                            onPressed: () =>
                                _navigate(SettingsScreen(api: widget.api)),
                            icon: const Glyph('settings'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 38),
                      Row(
                        children: [
                          Container(
                            width: 5,
                            height: 5,
                            decoration: const BoxDecoration(
                              color: lime,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 9),
                          Expanded(
                            child: Eyebrow(
                              profile == null
                                  ? 'A very serious security ritual'
                                  : 'Welcome back, ${profile['pseudo']}',
                              color: lime,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 17),
                      Text(
                        'Maximum security.',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      Text(
                        'Minimum secret.',
                        style: Theme.of(context).textTheme.headlineLarge
                            ?.copyWith(color: muted),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Your face. Your moves. Your signature.\nSome things deserve every layer.',
                        style: TextStyle(
                          color: muted,
                          fontSize: 14,
                          height: 1.6,
                        ),
                      ),
                      const SizedBox(height: 22),
                      Center(
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            const VaultDoor(size: 270),
                            Positioned(
                              right: 0,
                              bottom: 12,
                              child: Transform.rotate(
                                angle: -0.07,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 13,
                                    vertical: 9,
                                  ),
                                  decoration: BoxDecoration(
                                    color: lime,
                                    borderRadius: BorderRadius.circular(7),
                                  ),
                                  child: const Text(
                                    'NOTHING TO HIDE.\nEVERYTHING TO LOCK.',
                                    style: TextStyle(
                                      color: ink,
                                      fontSize: 8,
                                      height: 1.5,
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: 1,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 22),
                      Row(
                        children: [
                          for (final layer in ['face', 'body', 'hand'])
                            Expanded(
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Glyph(layer, size: 19, color: muted),
                                  const SizedBox(width: 8),
                                  Eyebrow(
                                    layer,
                                    color:
                                        (profile?['enrolled'] as List? ?? [])
                                            .contains(layer)
                                        ? lime
                                        : muted,
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 28),
                      VaultButton(
                        profile == null ? 'Create your vault' : 'Open my vault',
                        onPressed: _open,
                        busy: busy,
                      ),
                      const SizedBox(height: 10),
                      Center(
                        child: TextButton(
                          onPressed: () => _navigate(
                            profile == null
                                ? const AboutScreen()
                                : RitualScreen(api: widget.api),
                          ),
                          child: Text(
                            profile == null
                                ? 'What are we protecting, exactly?'
                                : 'Edit your security ritual',
                            style: const TextStyle(color: muted, fontSize: 12),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 18,
                        runSpacing: 8,
                        children: [
                          Eyebrow(
                            health?['ready'] == true
                                ? 'System online'
                                : 'Find your computer in Settings',
                            color: health?['ready'] == true ? lime : muted,
                          ),
                          const Eyebrow('No images stored / v.01'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

bool demoMode = false;
void showError(BuildContext context, Object e) => ScaffoldMessenger.of(context)
    .showSnackBar(
      SnackBar(
        content: Text(friendlyError(e)),
        duration: const Duration(seconds: 6),
      ),
    );

class PageShell extends StatelessWidget {
  final String label;
  final Widget child;
  const PageShell({super.key, required this.label, required this.child});
  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 28, 8),
                child: Row(
                  children: [
                    IconButton(
                      tooltip: 'Back',
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Text('←', style: TextStyle(fontSize: 26)),
                    ),
                    const SizedBox(width: 8),
                    Eyebrow(label),
                    const Spacer(),
                    const Glyph('vault', color: lime),
                  ],
                ),
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(28, 20, 28, 36),
                  child: child,
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class ConsentScreen extends StatefulWidget {
  final VaultApi api;
  const ConsentScreen({super.key, required this.api});
  @override
  State<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<ConsentScreen> {
  final pseudo = TextEditingController();
  bool consent = false, busy = false;
  @override
  void dispose() {
    pseudo.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    setState(() => busy = true);
    try {
      await widget.api.register(pseudo.text.trim());
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => RitualScreen(api: widget.api)),
      );
    } catch (e) {
      if (mounted) {
        showError(context, e);
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => PageShell(
    label: '01 / Before the ritual',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Glyph('hand', size: 42, color: lime),
        const SizedBox(height: 28),
        Text(
          'Your body.\nYour permission.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 18),
        const Text(
          'The joke is about privacy. Our promise is serious.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 28),
        const Bezel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Eyebrow('What actually happens', color: lime),
              SizedBox(height: 18),
              Text('01   Your camera sends frames to your local server.'),
              SizedBox(height: 16),
              Text(
                '02   Frames become movement landmarks. Images are discarded.',
              ),
              SizedBox(height: 16),
              Text(
                '03   Encrypted templates stay until you delete your vault. Attempt logs expire after 30 days.',
              ),
              SizedBox(height: 16),
              Text(
                'This is a biometric demonstration. It does not protect real secrets.',
                style: TextStyle(color: muted, fontSize: 12),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: pseudo,
          maxLength: 32,
          autocorrect: false,
          decoration: const InputDecoration(
            labelText: 'Choose a pseudonym',
            hintText: 'No email. No real name.',
          ),
        ),
        const SizedBox(height: 8),
        CheckboxListTile(
          value: consent,
          onChanged: (v) => setState(() => consent = v ?? false),
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text(
            'I explicitly consent to camera capture and biometric template processing for this demonstration.',
            style: TextStyle(fontSize: 13, height: 1.5),
          ),
        ),
        const SizedBox(height: 22),
        VaultButton(
          'I’m in. Create my vault.',
          onPressed: consent ? _create : null,
          busy: busy,
        ),
        const SizedBox(height: 8),
        Center(
          child: TextButton(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => SettingsScreen(api: widget.api),
              ),
            ),
            child: const Text(
              'Configure local server',
              style: TextStyle(color: muted),
            ),
          ),
        ),
      ],
    ),
  );
}

class RitualScreen extends StatefulWidget {
  final VaultApi api;
  const RitualScreen({super.key, required this.api});
  @override
  State<RitualScreen> createState() => _RitualScreenState();
}

class _RitualScreenState extends State<RitualScreen> {
  late List<String> selected;
  late bool randomized;
  bool busy = false;
  @override
  void initState() {
    super.initState();
    selected = List<String>.from(
      widget.api.profile?['sequence'] ?? ['face', 'body', 'hand'],
    );
    randomized = widget.api.profile?['randomized'] == true;
  }

  String get level => randomized
      ? 'Certified conspiracist'
      : ['Cautious', 'Suspicious', 'Whistleblower'][selected.length - 1];
  Future<void> _save() async {
    setState(() => busy = true);
    try {
      await widget.api.request(
        'PUT',
        '/api/v1/users/${widget.api.profile!['id']}/sequence',
        data: {'layers': selected, 'randomized': randomized},
      );
      await widget.api.refreshProfile();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Ritual saved. Your order, your rules.'),
          ),
        );
      }
    } catch (e) {
      if (mounted) showError(context, e);
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _enroll(String layer) async {
    setState(() => busy = true);
    try {
      final session = await widget.api.start(layer, true);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => CaptureScreen(
            api: widget.api,
            session: session,
            enrollment: true,
          ),
        ),
      );
      await widget.api.refreshProfile();
    } catch (e) {
      if (mounted) showError(context, e);
    }
    if (mounted) setState(() => busy = false);
  }

  @override
  Widget build(BuildContext context) => PageShell(
    label: '02 / Design your ritual',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'How much\nparanoia?',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 16),
        const Text(
          'Choose one to three layers. Teach the vault your moves, then set their order.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 28),
        Bezel(
          child: Row(
            children: [
              Text(
                '0${selected.length}',
                style: const TextStyle(
                  fontSize: 48,
                  color: lime,
                  letterSpacing: -3,
                ),
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Eyebrow('Your security level'),
                    const SizedBox(height: 6),
                    Text(level, style: const TextStyle(fontSize: 19)),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        for (final layer in ['face', 'body', 'hand'])
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Bezel(
              padding: const EdgeInsets.fromLTRB(18, 15, 10, 15),
              child: Column(
                children: [
                  Row(
                    children: [
                      Glyph(
                        layer,
                        size: 28,
                        color: selected.contains(layer) ? lime : muted,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              {
                                'face': 'Your secret expression',
                                'body': 'Your signature moves',
                                'hand': 'Your air signature',
                              }[layer]!,
                              style: const TextStyle(fontSize: 16),
                            ),
                            Text(
                              {
                                'face': '2 repetitions · face + expressions',
                                'body': '3 repetitions · 3–6 second dance',
                                'hand': '5 repetitions · pinch, draw, pinch',
                              }[layer]!,
                              style: const TextStyle(
                                color: muted,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Switch(
                        value: selected.contains(layer),
                        onChanged: busy
                            ? null
                            : (v) => setState(() {
                                if (v) {
                                  selected.add(layer);
                                } else if (selected.length > 1) {
                                  selected.remove(layer);
                                  randomized = false;
                                }
                              }),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      TextButton(
                        onPressed: busy ? null : () => _enroll(layer),
                        child: Text(
                          (widget.api.profile?['enrolled'] as List? ?? [])
                                  .contains(layer)
                              ? '✓ Recorded · record again'
                              : 'Record this layer ↗',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 18),
        const Eyebrow('Challenge order'),
        const SizedBox(height: 10),
        for (var i = 0; i < selected.length; i++)
          Row(
            children: [
              Text('0${i + 1}', style: const TextStyle(color: muted)),
              const SizedBox(width: 16),
              Expanded(child: Text(selected[i].toUpperCase())),
              IconButton(
                tooltip: 'Move ${selected[i]} earlier',
                onPressed: i == 0 || busy
                    ? null
                    : () => setState(() {
                        final value = selected.removeAt(i);
                        selected.insert(i - 1, value);
                      }),
                icon: const Text('↑', style: TextStyle(fontSize: 24)),
              ),
            ],
          ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: randomized,
          onChanged: selected.length == 3 && !busy
              ? (v) => setState(() => randomized = v)
              : null,
          title: const Text('Keep me guessing', style: TextStyle(fontSize: 15)),
          subtitle: const Text(
            'Shuffle all three + add a random extra challenge.',
            style: TextStyle(color: muted, fontSize: 11),
          ),
        ),
        const SizedBox(height: 22),
        VaultButton('Save my ritual', onPressed: _save, busy: busy),
      ],
    ),
  );
}

class SettingsScreen extends StatefulWidget {
  final VaultApi api;
  const SettingsScreen({super.key, required this.api});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController server;
  String status = '';
  bool busy = false;
  List<VaultServer> nearby = [];
  @override
  void initState() {
    super.initState();
    server = TextEditingController(text: widget.api.baseUrl);
  }

  @override
  void dispose() {
    server.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    setState(() => busy = true);
    try {
      await widget.api.setServer(server.text);
      final health = await widget.api.request('GET', '/api/v1/health');
      status = 'Connected · ${health['services']['scoring']['engine']}';
      if (widget.api.managementToken != null) await widget.api.refreshProfile();
    } catch (e) {
      status = friendlyError(e);
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _discover() async {
    setState(() {
      busy = true;
      status = 'Looking for THE VAULT on your Wi-Fi…';
    });
    try {
      nearby = await widget.api.findServers();
      server.text = widget.api.baseUrl;
      status = widget.api.connectionNotice ?? '';
    } catch (e) {
      status = friendlyError(e);
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _pair(VaultServer selected) async {
    setState(() => busy = true);
    try {
      await widget.api.connectServer(selected);
      server.text = widget.api.baseUrl;
      status = widget.api.connectionNotice ?? '';
    } catch (e) {
      status = friendlyError(e);
    }
    if (mounted) setState(() => busy = false);
  }

  Future<void> _delete() async {
    setState(() => busy = true);
    try {
      await widget.api.deleteAccount();
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      if (mounted) {
        showError(context, e);
        setState(() => busy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => PageShell(
    label: 'Control room',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Your vault.\nYour rules.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 28),
        const Eyebrow('Your computer'),
        const SizedBox(height: 12),
        Text(
          widget.api.serverName ?? 'Connect automatically on the same Wi-Fi',
          style: const TextStyle(color: muted),
        ),
        const SizedBox(height: 16),
        VaultButton(
          'Find my computer',
          onPressed: busy ? null : _discover,
          busy: busy,
        ),
        for (final computer in nearby)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(computer.name),
            subtitle: Text(
              computer.id == widget.api.serverId
                  ? 'Paired computer'
                  : 'Available on this network',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: busy ? null : () => _pair(computer),
          ),
        const SizedBox(height: 20),
        const Eyebrow('Advanced / HTTPS address'),
        const SizedBox(height: 12),
        TextField(
          controller: server,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(labelText: 'HTTPS address'),
        ),
        const SizedBox(height: 16),
        VaultButton(
          'Test connection',
          onPressed: busy ? null : _connect,
          busy: busy,
          secondary: true,
        ),
        if (status.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(
              status,
              style: const TextStyle(color: lime, fontSize: 12),
            ),
          ),
        const SizedBox(height: 16),
        const Text(
          'Start the desktop server and join the same Wi-Fi. The app remembers your computer and follows address changes. Pair for the first time on a network you trust.',
          style: TextStyle(color: muted, fontSize: 12),
        ),
        const SizedBox(height: 30),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: demoMode,
          onChanged: (v) => setState(() => demoMode = v),
          title: const Text('Demonstration mode'),
          subtitle: const Text(
            'Landmarks, latency, FPS and decision scores',
            style: TextStyle(color: muted, fontSize: 12),
          ),
        ),
        const SizedBox(height: 24),
        const Bezel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Eyebrow('Privacy by design', color: lime),
              SizedBox(height: 14),
              Text(
                'Raw images are never saved. Templates are encrypted. Nobody needs your contacts to protect a meme.',
              ),
            ],
          ),
        ),
        const SizedBox(height: 28),
        if (widget.api.profile != null) ...[
          const Text('Delete my vault', style: TextStyle(fontSize: 20)),
          const SizedBox(height: 10),
          const Text(
            'Permanently removes your templates, account and attempt logs. Active sessions and access tokens stop working immediately.',
            style: TextStyle(color: muted, fontSize: 13),
          ),
          const SizedBox(height: 16),
          VaultButton(
            'Delete all my data',
            onPressed: busy ? null : _delete,
            secondary: true,
          ),
        ],
        const SizedBox(height: 16),
        Center(
          child: TextButton(
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const AboutScreen())),
            child: const Text('Why THE VAULT exists'),
          ),
        ),
      ],
    ),
  );
}

class RevealScreen extends StatefulWidget {
  final VaultApi api;
  const RevealScreen({super.key, required this.api});
  @override
  State<RevealScreen> createState() => _RevealScreenState();
}

class _RevealScreenState extends State<RevealScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController animation;
  Map<String, dynamic>? data;
  Uint8List? meme;
  String? error;
  @override
  void initState() {
    super.initState();
    animation = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    );
    _load();
  }

  Future<void> _load() async {
    try {
      data = await widget.api.request('GET', '/api/v1/vault', vault: true);
      meme = await widget.api.image(data!['meme_url']);
      if (mounted) {
        animation.forward();
        HapticFeedback.heavyImpact();
        SystemSound.play(SystemSoundType.click);
        setState(() {});
      }
    } catch (e) {
      if (mounted) setState(() => error = friendlyError(e));
    }
  }

  @override
  void dispose() {
    animation.dispose();
    widget.api.accessToken = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => PageShell(
    label: 'Access granted',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Eyebrow('All that security. All for this.', color: lime),
        const SizedBox(height: 16),
        Text(
          'Your secret\nis safe.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 24),
        if (error != null)
          Text(error!)
        else
          AnimatedBuilder(
            animation: animation,
            builder: (context, child) {
              final t = motion.transform(animation.value);
              return SizedBox(
                height: 330,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    if (meme != null)
                      Opacity(
                        opacity: t,
                        child: Transform.scale(
                          scale: 0.85 + 0.15 * t,
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(26),
                            child: Image.memory(meme!, fit: BoxFit.contain),
                          ),
                        ),
                      ),
                    if (t < 1)
                      Opacity(
                        opacity: 1 - t,
                        child: Transform.translate(
                          offset: Offset(180 * t, 0),
                          child: VaultDoor(rotation: t * 2.6),
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
        const SizedBox(height: 22),
        Text(
          data?['caption'] ?? 'Releasing three extremely unnecessary locks…',
          style: const TextStyle(color: muted),
        ),
        const SizedBox(height: 26),
        if (data != null)
          VaultButton(
            'And my real data?',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => TransparencyScreen(data: data!['transparency']),
              ),
            ),
          ),
        const SizedBox(height: 14),
        Center(
          child: TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Lock it again'),
          ),
        ),
      ],
    ),
  );
}

class TransparencyScreen extends StatelessWidget {
  final Map<String, dynamic> data;
  const TransparencyScreen({super.key, required this.data});
  @override
  Widget build(BuildContext context) => PageShell(
    label: 'The punchline',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Eyebrow('An entirely fictional dashboard', color: lime),
        const SizedBox(height: 20),
        Text(
          'Meanwhile,\nelsewhere.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 28),
        Text(
          '${data['partners']}',
          style: const TextStyle(
            fontSize: 100,
            height: 1,
            letterSpacing: -7,
            color: lime,
          ),
        ),
        const Text(
          'imaginary partners already know you.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 32),
        for (final item in data['categories'])
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Row(
              children: [
                Expanded(child: Text(item['label'])),
                Text(
                  '${item['count']}',
                  style: const TextStyle(color: lime, fontSize: 22),
                ),
              ],
            ),
          ),
        const SizedBox(height: 24),
        Bezel(
          child: Text(
            data['notice'],
            style: const TextStyle(fontSize: 13, color: muted),
          ),
        ),
        const SizedBox(height: 26),
        VaultButton(
          'Take back some privacy',
          onPressed: () => launchUrl(
            Uri.parse(data['learn_url']),
            mode: LaunchMode.externalApplication,
          ),
        ),
      ],
    ),
  );
}

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});
  @override
  Widget build(BuildContext context) => PageShell(
    label: 'A serious joke',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Glyph('vault', size: 52, color: lime),
        const SizedBox(height: 32),
        Text(
          'A fortress.\nFor a meme.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 24),
        const Text(
          'THE VAULT asks for your face, a secret dance and a signature drawn in the air. Behind all those locks? One image.',
        ),
        const SizedBox(height: 20),
        const Text(
          'The recognition is real. The overkill is intentional. It’s a small satire about how much effort we put into locks while overlooking what happens to our data elsewhere.',
          style: TextStyle(color: muted),
        ),
        const SizedBox(height: 28),
        const Bezel(
          child: Text(
            'This is a demonstration, not a certified biometric security product. The transparency dashboard is fiction. Your permission is not.',
          ),
        ),
      ],
    ),
  );
}
