import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/localization/app_strings.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/app_button.dart';
import '../../../../core/widgets/app_loader.dart';
import '../controllers/review_controller.dart';

class ReviewsPage extends ConsumerStatefulWidget {
  final int propertyId;

  const ReviewsPage({
    super.key,
    required this.propertyId,
  });

  @override
  ConsumerState<ReviewsPage> createState() => _ReviewsPageState();
}

class _ReviewsPageState extends ConsumerState<ReviewsPage> {
  final titleController = TextEditingController();
  final commentController = TextEditingController();
  int rating = 5;

  @override
  void initState() {
    super.initState();
    Future.microtask(
      () => ref.read(reviewControllerProvider.notifier).load(widget.propertyId),
    );
  }

  @override
  void dispose() {
    titleController.dispose();
    commentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final ok = await ref.read(reviewControllerProvider.notifier).create(
          propertyId: widget.propertyId,
          rating: rating,
          title: titleController.text.trim(),
          comment: commentController.text.trim(),
        );

    if (!mounted) return;

    if (ok) {
      titleController.clear();
      commentController.clear();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Review submitted".tr(context))),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          (ref.read(reviewControllerProvider).error ?? "Failed").tr(context),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(reviewControllerProvider);

    return Scaffold(
      backgroundColor: AppTheme.ivory,
      appBar: AppBar(
        backgroundColor: AppTheme.ivory,
        title: Text(
          "Reviews".tr(context),
          style: const TextStyle(
            color: AppTheme.darkText,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: Builder(
              builder: (_) {
                if (state.isLoading) {
                  return const AppLoader();
                }

                return ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            "Write a Review".tr(context),
                            style: const TextStyle(
                              color: AppTheme.darkText,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 12),
                          DropdownButtonFormField<int>(
                            initialValue: rating,
                            items: [1, 2, 3, 4, 5]
                                .map(
                                  (e) => DropdownMenuItem(
                                    value: e,
                                    child: Text("$e ${"Star".tr(context)}"),
                                  ),
                                )
                                .toList(),
                            onChanged: (value) {
                              setState(() {
                                rating = value ?? 5;
                              });
                            },
                            decoration: InputDecoration(
                              labelText: "Rating".tr(context),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: titleController,
                            decoration: InputDecoration(
                              labelText: "Title".tr(context),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: commentController,
                            maxLines: 4,
                            decoration: InputDecoration(
                              labelText: "Comment".tr(context),
                              alignLabelWithHint: true,
                            ),
                          ),
                          const SizedBox(height: 16),
                          AppButton(
                            text: "Submit Review".tr(context),
                            isLoading: state.isSubmitting,
                            onPressed: _submit,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),
                    Text(
                      "Guest Reviews".tr(context),
                      style: const TextStyle(
                        color: AppTheme.darkText,
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 12),
                    if (state.reviews.isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 12),
                        child: Text(
                          "No reviews yet.".tr(context),
                          style: const TextStyle(color: AppTheme.mutedText),
                        ),
                      )
                    else
                      ...state.reviews.map(
                        (review) => Container(
                          margin: const EdgeInsets.only(bottom: 12),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                review.title.isEmpty
                                    ? "Guest Review".tr(context)
                                    : review.title,
                                style: const TextStyle(
                                  color: AppTheme.darkText,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                "${review.customerName} - ${review.rating}/5",
                                style:
                                    const TextStyle(color: AppTheme.mutedText),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                review.comment.isEmpty
                                    ? "No comment added.".tr(context)
                                    : review.comment,
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
