import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Luxury Dark Color Palette based on reference design
  static const Color background = Color(0xFF000000); // Pure OLED black
  static const Color surface = Color(0xFF1C1C1E); // iOS dark surface
  static const Color primary = Color(0xFFF3EAD3); // Elegant light beige/gold
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFFA0A0A0);
  static const Color positiveYield = Color(0xFF30D158); // iOS Green

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      primaryColor: primary,
      textTheme: TextTheme(
        displayLarge: GoogleFonts.playfairDisplay( // Serif for luxury/big numbers
          color: textPrimary,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
        ),
        headlineMedium: GoogleFonts.playfairDisplay(
          color: textPrimary,
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: GoogleFonts.inter( // Clean sans-serif for reading
          color: textPrimary,
          fontSize: 16,
        ),
        bodyMedium: GoogleFonts.inter(
          color: textSecondary,
          fontSize: 14,
        ),
        labelLarge: GoogleFonts.inter( // For Buttons
          color: background,
          fontWeight: FontWeight.bold,
          fontSize: 16,
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: background,
        elevation: 0,
        centerTitle: true,
      ),
      cardColor: surface,
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: background,
          minimumSize: const Size(double.infinity, 56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w600,
            fontSize: 16,
          ),
        ),
      ),
    );
  }
}
