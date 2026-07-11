import 'dart:convert';
import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../core/i18n/app_i18n.dart';
import '../../../../core/realtime/realtime_service.dart';
import '../../../../core/services/telemetry_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../data/models/operations_models.dart';
import '../../../auth/controllers/admin_access_controller.dart';
import '../../../auth/controllers/admin_session_controller.dart';
import '../../../dashboard/controllers/admin_dashboard_controller.dart';
import '../../../dashboard/controllers/selected_property_controller.dart';
import '../../../dashboard/presentation/widgets/admin_bottom_nav.dart';

class NotificationsPage extends StatefulWidget {
  final AdminAccessController? accessController;
  final AdminSessionController? sessionController;
  final AdminDashboardController? dashboardController;
  final RealtimeService? realtimeService;

  const NotificationsPage({
    super.key,
    this.accessController,
    this.sessionController,
    this.dashboardController,
    this.realtimeService,
  });

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  late final AdminAccessController _access;
  late final AdminSessionController _sessionController;
  late final AdminDashboardController _controller;
  late final RealtimeService _realtimeService;
  StreamSubscription<DateTime>? _tickSubscription;
  final TextEditingController _notesController = TextEditingController();

  bool _isLoading = true;
  bool _isSaving = false;
  bool _isRunningAction = false;
  String? _error;

  NotificationSettingItem? _setting;
  bool _enableWhatsApp = true;
  String _defaultChannel = 'whatsapp';
  List<SecurityAlertItem> _alerts = const [];
  bool _showUnreadOnly = true;

  final Map<String, String> _roleChannels = {
    'owner_admin': 'whatsapp',
    'manager': 'whatsapp',
    'reception': 'email',
    'housekeeping': 'whatsapp',
    'maintenance': 'whatsapp',
  };

  bool _escalationEnabled = true;
  int _escalationAfterMinutes = 30;
  String _escalationChannel = 'email';

  String _channelText(String key) {
    if (key == 'whatsapp') return context.tr('channel_whatsapp');
    if (key == 'email') return context.tr('channel_email');
    if (key == 'sms') return context.tr('channel_sms');
    return key;
  }

  String _roleText(String key) {
    if (key == 'owner_admin') return context.tr('owner_admin');
    if (key == 'manager') return context.tr('manager');
    if (key == 'reception') return context.tr('reception');
    if (key == 'housekeeping') return context.tr('housekeeping');
    if (key == 'maintenance') return context.tr('maintenance');
    return key;
  }

  @override
  void initState() {
    super.initState();
    _access = widget.accessController ?? AdminAccessController();
    _sessionController = widget.sessionController ?? AdminSessionController();
    _controller = widget.dashboardController ?? AdminDashboardController();
    _realtimeService = widget.realtimeService ?? PollingRealtimeService();
    TelemetryService.instance.trackScreen('notifications');
    SelectedPropertyController.ensureDefault(
      _sessionController.getPropertyIds(),
    );
    _load();
    _tickSubscription = _realtimeService.ticks.listen(
      (_) => _load(silent: true),
    );
    _realtimeService.start();
  }

  @override
  void dispose() {
    _tickSubscription?.cancel();
    _realtimeService.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final propertyId = SelectedPropertyController.selectedPropertyId;
      if (propertyId == null || propertyId.isEmpty) {
        throw Exception('No property selected');
      }

      final results = await Future.wait([
        _controller.loadNotificationSetting(propertyId: propertyId),
        _controller.loadSecurityAlerts(propertyId: propertyId),
      ]);

      if (!mounted) return;
      final setting = results[0] as NotificationSettingItem?;
      final alerts = results[1] as List<SecurityAlertItem>;

      setState(() {
        _setting = setting;
        _enableWhatsApp = setting?.enableWhatsApp ?? true;
        _defaultChannel = setting?.defaultChannel ?? 'whatsapp';
        _alerts = alerts;
      });

      _applyStructuredNotes(setting?.notes ?? '');
      if (mounted) {
        setState(() {});
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted && !silent) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _applyStructuredNotes(String rawNotes) {
    if (rawNotes.trim().isEmpty) {
      _notesController.text = '';
      return;
    }

    try {
      final decoded = jsonDecode(rawNotes);
      if (decoded is! Map<String, dynamic>) {
        _notesController.text = rawNotes;
        return;
      }

      _notesController.text = (decoded['admin_note'] ?? '').toString();

      final roleChannelsRaw = decoded['role_channels'];
      if (roleChannelsRaw is Map<String, dynamic>) {
        for (final entry in roleChannelsRaw.entries) {
          final channel = entry.value.toString();
          if (_isValidChannel(channel)) {
            _roleChannels[entry.key] = channel;
          }
        }
      }

      final escalationRaw = decoded['escalation'];
      if (escalationRaw is Map<String, dynamic>) {
        _escalationEnabled = escalationRaw['enabled'] == true;
        final after = int.tryParse(
          (escalationRaw['after_minutes'] ?? '').toString(),
        );
        _escalationAfterMinutes = after == null || after <= 0 ? 30 : after;

        final channel = (escalationRaw['channel'] ?? '').toString();
        if (_isValidChannel(channel)) {
          _escalationChannel = channel;
        }
      }
    } catch (_) {
      _notesController.text = rawNotes;
    }
  }

  bool _isValidChannel(String channel) {
    return channel == 'whatsapp' || channel == 'email' || channel == 'sms';
  }

  String _buildNotesJson() {
    return jsonEncode({
      'admin_note': _notesController.text.trim(),
      'role_channels': _roleChannels,
      'escalation': {
        'enabled': _escalationEnabled,
        'after_minutes': _escalationAfterMinutes,
        'channel': _escalationChannel,
      },
    });
  }

  Future<void> _save() async {
    final propertyId = SelectedPropertyController.selectedPropertyId;
    if (propertyId == null || propertyId.isEmpty) return;

    setState(() => _isSaving = true);
    try {
      NotificationSettingItem saved;
      final notesJson = _buildNotesJson();
      if (_setting == null) {
        saved = await _controller.createNotificationSetting(
          propertyId: propertyId,
          enableWhatsApp: _enableWhatsApp,
          defaultChannel: _defaultChannel,
          notes: notesJson,
        );
      } else {
        saved = await _controller.updateNotificationSetting(
          settingId: _setting!.id,
          enableWhatsApp: _enableWhatsApp,
          defaultChannel: _defaultChannel,
          notes: notesJson,
        );
      }

      if (!mounted) return;
      setState(() => _setting = saved);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('notification_settings_saved'))),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(content: Text(context.tr('save_failed', params: {'error': '$e'}))),
      );
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _markRead(int id) async {
    setState(() => _isRunningAction = true);
    try {
      await _controller.markNotificationRead(id);
      await _load(silent: true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(content: Text(context.tr('failed_mark_as_read', params: {'error': '$e'}))),
      );
    } finally {
      if (mounted) {
        setState(() => _isRunningAction = false);
      }
    }
  }

  Future<void> _markAllVisibleRead() async {
    final items = _visibleAlerts.where((a) => !a.isRead).toList();
    if (items.isEmpty) return;

    setState(() => _isRunningAction = true);
    try {
      for (final item in items) {
        await _controller.markNotificationRead(item.id);
      }
      await _load(silent: true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(content: Text(context.tr('failed_mark_all_read', params: {'error': '$e'}))),
      );
    } finally {
      if (mounted) {
        setState(() => _isRunningAction = false);
      }
    }
  }

  List<SecurityAlertItem> get _visibleAlerts {
    if (!_showUnreadOnly) return _alerts;
    return _alerts.where((a) => !a.isRead).toList();
  }

  bool _isEscalationCandidate(SecurityAlertItem item) {
    if (!_escalationEnabled) return false;
    if (item.status != 'failed') return false;

    final createdAt = DateTime.tryParse(item.createdAt);
    if (createdAt == null) return true;

    final elapsed = DateTime.now().difference(createdAt.toLocal());
    return elapsed.inMinutes >= _escalationAfterMinutes;
  }

  @override
  Widget build(BuildContext context) {
    final unreadCount = _alerts.where((a) => !a.isRead).length;

    return Scaffold(
      appBar: AppBar(
        title: Text(context.tr('notifications')),
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
      ),
      backgroundColor: AppTheme.lightBg,
      bottomNavigationBar: AdminBottomNav(
        currentRoute: '/admin/notifications',
        showStaffTab: _access.canManageStaff(),
        showSecurityTab: _access.canManageSecurity(),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      context.tr('failed_load_notifications', params: {'error': '$_error'}),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    FilledButton(onPressed: _load, child: Text(context.tr('retry'))),
                  ],
                ),
              ),
            )
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.tr('notification_preferences'),
                          style: TextStyle(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 8),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _enableWhatsApp,
                          onChanged: (v) => setState(() => _enableWhatsApp = v),
                          title: Text(context.tr('enable_whatsapp')),
                        ),
                        const SizedBox(height: 8),
                        DropdownButtonFormField<String>(
                          initialValue: _defaultChannel,
                          items: [
                            DropdownMenuItem(
                              value: 'whatsapp',
                              child: Text(_channelText('whatsapp')),
                            ),
                            DropdownMenuItem(
                              value: 'email',
                              child: Text(_channelText('email')),
                            ),
                            DropdownMenuItem(value: 'sms', child: Text(_channelText('sms'))),
                          ],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => _defaultChannel = v);
                          },
                          decoration: InputDecoration(
                            labelText: context.tr('default_channel'),
                            filled: true,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          context.tr('role_channel_preferences'),
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        ..._roleChannels.keys.map((role) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              children: [
                                SizedBox(width: 120, child: Text(_roleText(role))),
                                Expanded(
                                  child: DropdownButtonFormField<String>(
                                    initialValue: _roleChannels[role],
                                    items: [
                                      DropdownMenuItem(
                                        value: 'whatsapp',
                                        child: Text(_channelText('whatsapp')),
                                      ),
                                      DropdownMenuItem(
                                        value: 'email',
                                        child: Text(_channelText('email')),
                                      ),
                                      DropdownMenuItem(
                                        value: 'sms',
                                        child: Text(_channelText('sms')),
                                      ),
                                    ],
                                    onChanged: (v) {
                                      if (v == null) return;
                                      setState(() => _roleChannels[role] = v);
                                    },
                                  ),
                                ),
                              ],
                            ),
                          );
                        }),
                        const SizedBox(height: 8),
                        Text(
                          context.tr('escalation_rule'),
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          value: _escalationEnabled,
                          onChanged: (v) =>
                              setState(() => _escalationEnabled = v),
                          title: Text(context.tr('escalate_failed_alerts')),
                        ),
                        Row(
                          children: [
                            Expanded(
                              child: TextFormField(
                                initialValue: _escalationAfterMinutes
                                    .toString(),
                                keyboardType: TextInputType.number,
                                decoration: InputDecoration(
                                  labelText: context.tr('escalate_after_minutes'),
                                  filled: true,
                                ),
                                onChanged: (v) {
                                  final parsed = int.tryParse(v);
                                  if (parsed != null && parsed > 0) {
                                    _escalationAfterMinutes = parsed;
                                  }
                                },
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: DropdownButtonFormField<String>(
                                initialValue: _escalationChannel,
                                items: [
                                  DropdownMenuItem(
                                    value: 'whatsapp',
                                    child: Text(_channelText('whatsapp')),
                                  ),
                                  DropdownMenuItem(
                                    value: 'email',
                                    child: Text(_channelText('email')),
                                  ),
                                  DropdownMenuItem(
                                    value: 'sms',
                                    child: Text(_channelText('sms')),
                                  ),
                                ],
                                onChanged: (v) {
                                  if (v == null) return;
                                  setState(() => _escalationChannel = v);
                                },
                                decoration: InputDecoration(
                                  labelText: context.tr('escalation_channel'),
                                  filled: true,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _notesController,
                          minLines: 2,
                          maxLines: 4,
                          decoration: InputDecoration(
                            labelText: context.tr('admin_notes'),
                            filled: true,
                          ),
                        ),
                        const SizedBox(height: 10),
                        FilledButton(
                          onPressed: _isSaving ? null : _save,
                          child: Text(_isSaving ? context.tr('saving') : context.tr('save')),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                context.tr('notification_center'),
                                style: TextStyle(fontWeight: FontWeight.w700),
                              ),
                            ),
                            Chip(label: Text(context.tr('unread_count', params: {'count': '$unreadCount'}))),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            FilterChip(
                              selected: _showUnreadOnly,
                              onSelected: (v) =>
                                  setState(() => _showUnreadOnly = v),
                              label: Text(context.tr('unread_only')),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton(
                              onPressed: _isRunningAction
                                  ? null
                                  : _markAllVisibleRead,
                              child: Text(context.tr('mark_visible_read')),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        if (_visibleAlerts.isEmpty)
                          Text(context.tr('no_notification_events'))
                        else
                          ..._visibleAlerts.take(12).map((a) {
                            final escalated = _isEscalationCandidate(a);
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: Icon(
                                a.isRead
                                    ? Icons.mark_email_read_outlined
                                    : Icons.mark_email_unread_outlined,
                                color: a.isRead
                                    ? Colors.grey
                                    : AppTheme.primaryNavy,
                              ),
                              title: Row(
                                children: [
                                  Expanded(child: Text(a.title)),
                                  if (escalated)
                                    Chip(
                                      label: Text(context.tr('escalate')),
                                      backgroundColor: Color(0xFFFFE0B2),
                                    ),
                                ],
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('${_channelText(a.channel)} - ${context.tr(a.status)}'),
                                  Text(
                                    a.createdAt.isEmpty
                                        ? '-'
                                        : a.createdAt
                                              .replaceFirst('T', ' ')
                                              .split('.')
                                              .first,
                                    style: const TextStyle(fontSize: 12),
                                  ),
                                  if (a.error.trim().isNotEmpty)
                                    Text(
                                      a.error,
                                      style: const TextStyle(color: Colors.red),
                                    ),
                                ],
                              ),
                              trailing: TextButton(
                                onPressed: (_isRunningAction || a.isRead)
                                    ? null
                                    : () => _markRead(a.id),
                                child: Text(context.tr('read')),
                              ),
                            );
                          }),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}
