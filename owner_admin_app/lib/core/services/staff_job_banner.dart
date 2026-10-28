import 'dart:async';
import 'package:flutter/material.dart';
import '../../data/repositories/token_storage.dart';
import 'staff_job_notifications.dart';
import 'firebase_push_service.dart';

class StaffJobBanner extends StatefulWidget {
  final Widget child;
  final VoidCallback onOpen;
  const StaffJobBanner({super.key, required this.child, required this.onOpen});
  @override
  State<StaffJobBanner> createState() => _StaffJobBannerState();
}

class _StaffJobBannerState extends State<StaffJobBanner> with WidgetsBindingObserver {
  Timer? _timer;
  final inbox = StaffJobNotifications.instance;
  void start() {
    _timer?.cancel();
    inbox.refresh();
    FirebasePushService.instance.syncSession();
    _timer = Timer.periodic(const Duration(seconds: 20), (_) {
      inbox.refresh();
      FirebasePushService.instance.syncSession();
    });
  }
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) start(); });
  }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) { start(); } else { _timer?.cancel(); }
  }
  @override
  void dispose() {
    _timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
  @override
  Widget build(BuildContext context) => ListenableBuilder(listenable: inbox, builder: (context, _) => Column(children: [
    if (TokenStorage.currentToken != null && inbox.unreadCount > 0)
      Material(color: const Color(0xff12283f), child: SafeArea(bottom: false, child: InkWell(
        onTap: widget.onOpen,
        child: Padding(padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10), child: Row(children: [
          const Icon(Icons.notifications_active, color: Colors.white),
          const SizedBox(width: 12),
          Expanded(child: Text('${inbox.unreadCount} unread job notification(s)', style: const TextStyle(color: Colors.white))),
          const Icon(Icons.chevron_right, color: Colors.white),
        ])),
      ))),
    Expanded(child: widget.child),
  ]));
}
