import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_empty_state.dart';
import '../../../../core/widgets/app_error_state.dart';
import '../../../../core/widgets/app_loader.dart';
import '../controllers/wishlist_controller.dart';

class WishlistPage extends ConsumerStatefulWidget {
  const WishlistPage({super.key});

  @override
  ConsumerState<WishlistPage> createState() => _WishlistPageState();
}

class _WishlistPageState extends ConsumerState<WishlistPage> {
  final collectionController = TextEditingController();

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(wishlistControllerProvider.notifier).load());
  }

  @override
  void dispose() {
    collectionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(wishlistControllerProvider);

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Wishlist".tr(context),
          style: TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Builder(
        builder: (_) {
          if (state.isLoading) {
            return AppLoader(message: "Loading wishlist...".tr(context));
          }

          if (state.error != null && state.items.isEmpty) {
            return AppErrorState(
              message: state.error,
              onRetry: () => ref.read(wishlistControllerProvider.notifier).load(),
            );
          }

          if (state.items.isEmpty) {
            return AppEmptyState(
              icon: Icons.favorite_border_rounded,
              title: "No wishlist items yet".tr(context),
              message:
                  "Save properties you like and come back to them anytime."
                      .tr(context),
            );
          }

          return RefreshIndicator(
            onRefresh: () => ref.read(wishlistControllerProvider.notifier).load(),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: collectionController,
                              decoration: InputDecoration(
                                hintText: "Create collection".tr(context),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          FilledButton(
                            onPressed: () async {
                              final name = collectionController.text.trim();
                              if (name.isEmpty) return;
                              await ref
                                  .read(wishlistControllerProvider.notifier)
                                  .createCollection(name, isPublic: false);
                              collectionController.clear();
                            },
                            style: FilledButton.styleFrom(backgroundColor: AppTheme.primaryNavy),
                            child: Text("Add".tr(context)),
                          ),
                        ],
                      ),
                      if (state.collections.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        SizedBox(
                          height: 36,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemBuilder: (context, index) {
                              final c = state.collections[index];
                              return ActionChip(
                                label: Text((c["name"] ?? "").toString()),
                                onPressed: () async {
                                  final messenger = ScaffoldMessenger.of(this.context);
                                  final shareUrlLabel = "Share URL".tr(this.context);
                                  final id = int.tryParse((c["id"] ?? "0").toString()) ?? 0;
                                  final shared = await ref
                                      .read(wishlistControllerProvider.notifier)
                                      .shareCollection(id);
                                  if (!mounted) return;
                                  final url = (shared["share_url"] ?? "").toString();
                                  messenger.showSnackBar(
                                    SnackBar(
                                      content: Text(
                                        "$shareUrlLabel: $url",
                                      ),
                                    ),
                                  );
                                },
                              );
                            },
                            separatorBuilder: (_, __) => const SizedBox(width: 8),
                            itemCount: state.collections.length,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                ...state.items.map((item) {
                  return Container(
                    margin: const EdgeInsets.only(bottom: 14),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            const CircleAvatar(
                              backgroundColor: Color(0xFFF2E9CF),
                              child: Icon(Icons.favorite, color: AppTheme.luxuryGold),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: InkWell(
                                onTap: () => context.push("/property/${item.propertyId}"),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      item.propertyName,
                                      style: const TextStyle(
                                        color: AppTheme.darkText,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                    if (item.collectionName.trim().isNotEmpty)
                                      Text(
                                        "${"Collection".tr(context)}: ${item.collectionName}",
                                        style: const TextStyle(fontSize: 12, color: AppTheme.mutedText),
                                      ),
                                  ],
                                ),
                              ),
                            ),
                            IconButton(
                              onPressed: () => ref
                                  .read(wishlistControllerProvider.notifier)
                                  .toggle(item.propertyId, collectionId: item.collectionId),
                              icon: const Icon(Icons.delete_outline_rounded),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                item.lastKnownPrice == null
                                    ? "Price alert disabled".tr(context)
                                    : "${"Last known".tr(context)}: ${item.lastKnownPrice!.toStringAsFixed(0)}",
                                style: const TextStyle(fontSize: 12, color: AppTheme.mutedText),
                              ),
                            ),
                            Switch(
                              value: item.priceAlertEnabled,
                              onChanged: (v) async {
                                await ref
                                    .read(wishlistControllerProvider.notifier)
                                    .setPriceAlert(item.id, enabled: v, targetPrice: item.targetPrice);
                              },
                            ),
                          ],
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          );
        },
      ),
    );
  }
}
