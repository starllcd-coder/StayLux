import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/services/staff_job_notifications.dart';

class StaffJobsPage extends StatefulWidget {
  const StaffJobsPage({super.key});
  @override
  State<StaffJobsPage> createState() => _StaffJobsPageState();
}

class _StaffJobsPageState extends State<StaffJobsPage> {
  final inbox = StaffJobNotifications.instance;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) inbox.refresh(); });
  }

  Future<void> openJob(Map<String, dynamic> item) async {
    try {
      await inbox.markRead(item['id'] as int);
      if (!mounted) return;
      context.go(item['housekeeping_task'] != null ? '/admin/housekeeping' : '/admin/maintenance');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not open notification. Please retry.')));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('My Job Notifications'),
      leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => context.go('/admin/dashboard')),
      actions: [IconButton(onPressed: inbox.refresh, icon: const Icon(Icons.refresh))],
    ),
    body: ListenableBuilder(listenable: inbox, builder: (context, _) => RefreshIndicator(
      onRefresh: inbox.refresh,
      child: ListView(physics: const AlwaysScrollableScrollPhysics(), children: [
        if (inbox.error != null) Padding(padding: const EdgeInsets.all(16), child: Text(inbox.error!)),
        if (inbox.items.isEmpty && inbox.error == null)
          const Padding(padding: EdgeInsets.all(24), child: Text('No job notifications yet. Assigned housekeeping and maintenance jobs will appear here.')),
        for (final item in inbox.items) Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: ListTile(
            leading: Icon(item['housekeeping_task'] != null ? Icons.cleaning_services : Icons.build),
            title: Text(item['title'] as String, style: TextStyle(fontWeight: item['is_read'] == true ? FontWeight.normal : FontWeight.bold)),
            subtitle: Text('${item['message']}\n${item['created_at']}'),
            trailing: item['is_read'] == true ? null : const Icon(Icons.circle, size: 10, color: Colors.blue),
            onTap: () => openJob(item),
          ),
        ),
      ]),
    )),
  );
}
