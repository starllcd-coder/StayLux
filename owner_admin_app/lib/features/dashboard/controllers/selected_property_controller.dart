class SelectedPropertyController {
  static String? _selectedPropertyId;

  static String? get selectedPropertyId => _selectedPropertyId;

  static void setSelectedProperty(String propertyId) {
    _selectedPropertyId = propertyId;
  }

  static void ensureDefault(List<String> availablePropertyIds) {
    if (availablePropertyIds.isEmpty) return;
    _selectedPropertyId ??= availablePropertyIds.first;
    if (!availablePropertyIds.contains(_selectedPropertyId)) {
      _selectedPropertyId = availablePropertyIds.first;
    }
  }

  static void clear() {
    _selectedPropertyId = null;
  }
}