import 'package:flutter/material.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../data/datasources/profile_services_api.dart';

class ConciergePage extends StatefulWidget {
  const ConciergePage({super.key});

  @override
  State<ConciergePage> createState() => _ConciergePageState();
}

class _ConciergePageState extends State<ConciergePage> {
  final api = ProfileServicesApi(ApiClient());
  final notesController = TextEditingController();
  final dateController = TextEditingController();
  bool loading = true;
  List<Map<String, dynamic>> services = const [];
  List<Map<String, dynamic>> requests = const [];
  int? selectedServiceId;
  String requestDate = "";
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    notesController.dispose();
    dateController.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: DateTime(now.year + 2),
      initialDate: now,
    );
    if (picked == null) return;
    setState(() {
      requestDate =
          "${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}";
      dateController.text = requestDate;
    });
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final s = await api.getConciergeServices();
      final r = await api.getConciergeRequests();
      setState(() {
        services = s;
        requests = r;
        selectedServiceId = s.isNotEmpty ? _toInt(s.first["id"]) : null;
        loading = false;
      });
    } catch (e) {
      setState(() {
        loading = false;
        error = e.toString();
      });
    }
  }

  Future<void> _createRequest() async {
    if (selectedServiceId == null) return;
    try {
      await api.createConciergeRequest(
        serviceId: selectedServiceId!,
        requestedForDate: requestDate,
        notes: notesController.text.trim(),
      );
      notesController.clear();
      final r = await api.getConciergeRequests();
      setState(() => requests = r);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Concierge request submitted".tr(context))),
      );
    } catch (e) {
      setState(() => error = e.toString());
    }
  }

  int _toInt(dynamic v) => int.tryParse(v?.toString() ?? "") ?? 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Concierge".tr(context),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (error != null) Text(error!, style: const TextStyle(color: Colors.red)),
                  Text(
                    "Service Packages".tr(context),
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      Chip(label: Text("Honeymoon".tr(context))),
                      Chip(label: Text("Business Travel".tr(context))),
                      Chip(label: Text("Family Holiday".tr(context))),
                    ],
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<int>(
                    initialValue: selectedServiceId,
                    decoration: InputDecoration(labelText: "Service".tr(context)),
                    items: services
                        .map(
                          (s) => DropdownMenuItem(
                            value: _toInt(s["id"]),
                            child: Text((s["name"] ?? "").toString()),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => setState(() => selectedServiceId = value),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: dateController,
                    readOnly: true,
                    onTap: _pickDate,
                    decoration: InputDecoration(
                      labelText: "Requested Date".tr(context),
                      prefixIcon: Icon(Icons.calendar_month_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: notesController,
                    maxLines: 3,
                    decoration: InputDecoration(labelText: "Notes".tr(context)),
                  ),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _createRequest,
                    style: FilledButton.styleFrom(backgroundColor: AppTheme.luxuryGold),
                    child: Text("Request Service".tr(context)),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    "My Requests".tr(context),
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
                  ),
                  const SizedBox(height: 8),
                  if (requests.isEmpty)
                    Text("No requests yet.".tr(context))
                  else
                    ...requests.map(
                      (r) => Card(
                        child: ListTile(
                          title: Text(
                            (r["service_name"] ?? "Service".tr(context))
                                .toString(),
                          ),
                          subtitle: Text((r["status"] ?? "pending").toString()),
                          trailing: Text((r["quote_amount"] ?? "0").toString()),
                        ),
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}
