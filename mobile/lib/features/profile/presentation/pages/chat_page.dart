import 'package:flutter/material.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_theme.dart';
import '../../data/datasources/profile_services_api.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final api = ProfileServicesApi(ApiClient());
  final messageController = TextEditingController();
  final attachmentController = TextEditingController();
  bool loading = true;
  int? selectedConversationId;
  List<Map<String, dynamic>> messages = const [];
  List<String> templates = const [];
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    messageController.dispose();
    attachmentController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final conv = await api.getConversations();
      final t = await api.getChatTemplates();
      int convId = 0;
      if (conv.isNotEmpty) {
        convId = _toInt(conv.first["id"]);
      }
      if (convId <= 0) {
        final created = await api.createConversation(title: "Guest Support");
        convId = _toInt(created["id"]);
      }
      final msg = convId > 0 ? await api.getMessages(convId) : <Map<String, dynamic>>[];
      setState(() {
        templates = t;
        selectedConversationId = convId > 0 ? convId : null;
        messages = msg;
        loading = false;
      });
    } catch (e) {
      setState(() {
        loading = false;
        error = e.toString();
      });
    }
  }

  Future<void> _send() async {
    final text = messageController.text.trim();
    final convId = selectedConversationId;
    if (text.isEmpty || convId == null) return;
    try {
      await api.sendMessage(convId, text);
      messageController.clear();
      final msg = await api.getMessages(convId);
      setState(() => messages = msg);
    } catch (e) {
      setState(() => error = e.toString());
    }
  }

  Future<void> _sendWithAttachment() async {
    final text = messageController.text.trim();
    final convId = selectedConversationId;
    if (convId == null) return;
    final attachment = attachmentController.text.trim();
    if (text.isEmpty && attachment.isEmpty) return;
    try {
      await api.sendMessage(convId, text.isEmpty ? "Shared a file." : text, attachmentUrl: attachment);
      messageController.clear();
      attachmentController.clear();
      final msg = await api.getMessages(convId);
      setState(() => messages = msg);
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
          "Chat Support".tr(context),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                    child: Text(error!, style: const TextStyle(color: Colors.red)),
                  ),
                if (templates.isNotEmpty)
                  SizedBox(
                    height: 44,
                    child: ListView.separated(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      scrollDirection: Axis.horizontal,
                      itemBuilder: (context, index) {
                        final t = templates[index];
                        return ActionChip(
                          label: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis),
                          onPressed: () => setState(() => messageController.text = t),
                        );
                      },
                      separatorBuilder: (_, __) => const SizedBox(width: 8),
                      itemCount: templates.length,
                    ),
                  ),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final item = messages[index];
                      final isSystem = item["is_system"] == true;
                      final body = (item["body"] ?? "").toString();
                      final translated = (item["translated_body"] ?? "").toString();
                      final attachment = (item["attachment_url"] ?? "").toString();
                      return Align(
                        alignment: isSystem ? Alignment.centerLeft : Alignment.centerRight,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(12),
                          constraints: const BoxConstraints(maxWidth: 320),
                          decoration: BoxDecoration(
                            color: isSystem ? Colors.white : const Color(0xFFF2E9CF),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(body),
                              if (translated.trim().isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(
                                  translated,
                                  style: const TextStyle(color: AppTheme.mutedText, fontSize: 12),
                                ),
                              ],
                              if (attachment.trim().isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(
                                  "${"Attachment".tr(context)}: $attachment",
                                  style: const TextStyle(fontSize: 12, color: AppTheme.primaryNavy),
                                ),
                              ],
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
                  child: Column(
                    children: [
                      TextField(
                        controller: attachmentController,
                        decoration: InputDecoration(
                          hintText: "Attachment URL (optional)".tr(context),
                          prefixIcon: Icon(Icons.attach_file_rounded),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: messageController,
                              decoration: InputDecoration(
                                hintText: "Type a message...".tr(context),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton(
                            onPressed: _send,
                            style: FilledButton.styleFrom(backgroundColor: AppTheme.luxuryGold),
                            child: Text("Send".tr(context)),
                          ),
                          const SizedBox(width: 6),
                          OutlinedButton(
                            onPressed: _sendWithAttachment,
                            child: Text("Send File".tr(context)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
