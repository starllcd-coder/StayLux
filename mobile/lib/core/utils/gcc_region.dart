import 'dart:ui';

const List<String> gccCountries = <String>[
  "Oman",
  "Qatar",
  "United Arab Emirates",
  "Saudi Arabia",
  "Kuwait",
  "Bahrain",
];

String _normalizeCountry(String country) {
  return country.trim().toLowerCase();
}

String currencyForCountry(String country) {
  final normalized = _normalizeCountry(country);
  if (normalized == "oman") return "OMR";
  if (normalized == "qatar") return "QAR";
  if (normalized == "united arab emirates" || normalized == "uae") return "AED";
  if (normalized == "saudi arabia" || normalized == "ksa") return "SAR";
  if (normalized == "kuwait") return "KWD";
  if (normalized == "bahrain") return "BHD";
  return "GCC";
}

String countryCodeForCountry(String country) {
  final normalized = _normalizeCountry(country);
  if (normalized == "oman") return "OM";
  if (normalized == "qatar") return "QA";
  if (normalized == "united arab emirates" || normalized == "uae") return "AE";
  if (normalized == "saudi arabia" || normalized == "ksa") return "SA";
  if (normalized == "kuwait") return "KW";
  if (normalized == "bahrain") return "BH";
  return "";
}

({String city, String country}) parseDestinationInput(String raw) {
  final value = raw.trim();
  if (value.isEmpty) {
    return (city: "", country: "");
  }

  final lower = value.toLowerCase();
  const countryAliases = <String, String>{
    "oman": "Oman",
    "qatar": "Qatar",
    "united arab emirates": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "saudi arabia": "Saudi Arabia",
    "ksa": "Saudi Arabia",
    "kuwait": "Kuwait",
    "bahrain": "Bahrain",
  };
  final mapped = countryAliases[lower];
  if (mapped != null) {
    return (city: "", country: mapped);
  }

  if (value.contains(",")) {
    final parts = value.split(",");
    final city = parts.first.trim();
    final country = parts.skip(1).join(",").trim();
    return (city: city, country: country);
  }

  return (city: value, country: "");
}

String defaultBillingCountryCode() {
  final localeCountry = PlatformDispatcher.instance.locale.countryCode ?? "";
  if (localeCountry.length == 2) {
    return localeCountry.toUpperCase();
  }
  return "";
}
