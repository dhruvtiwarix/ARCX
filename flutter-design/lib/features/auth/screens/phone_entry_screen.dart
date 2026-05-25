import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'phone_otp_screen.dart';

class PhoneEntryScreen extends StatelessWidget {
  const PhoneEntryScreen({super.key});

  static const Color arcxBlack = Color(0xFF141414);
  static const Color arcxWhite = Color(0xFFFFFFFF);
  static const Color arcxGray = Color(0xFF1C1C1C);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: arcxBlack,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: arcxWhite, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Security Icon
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: arcxGray,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: arcxWhite.withValues(alpha: 0.1)),
                ),
                child: const Icon(Icons.shield_outlined, color: arcxWhite),
              ),
              const SizedBox(height: 32),
              
              // Header
              Text(
                'Secure Your Vault',
                style: GoogleFonts.playfairDisplay(
                  color: arcxWhite,
                  fontSize: 32,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'To deposit funds and access the ARCX settlement network, you must secure your account with a verified phone number.',
                style: GoogleFonts.inter(
                  color: arcxWhite.withValues(alpha: 0.6),
                  fontSize: 14,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 48),
              
              // Phone Input Field
              Text(
                'Phone Number',
                style: GoogleFonts.inter(
                  color: arcxWhite.withValues(alpha: 0.5),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Container(
                height: 56,
                decoration: BoxDecoration(
                  color: arcxGray,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: arcxWhite.withValues(alpha: 0.1)),
                ),
                child: Row(
                  children: [
                    // Country Code
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          Text(
                            '🇮🇳', 
                            style: GoogleFonts.inter(fontSize: 16),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '+91',
                            style: GoogleFonts.inter(
                              color: arcxWhite,
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Icon(Icons.keyboard_arrow_down, color: arcxWhite.withValues(alpha: 0.5), size: 16),
                        ],
                      ),
                    ),
                    Container(width: 1, height: 24, color: arcxWhite.withValues(alpha: 0.1)),
                    // Input
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: TextField(
                          keyboardType: TextInputType.phone,
                          style: GoogleFonts.inter(color: arcxWhite, fontSize: 16, letterSpacing: 1),
                          decoration: InputDecoration(
                            border: InputBorder.none,
                            hintText: '00000 00000',
                            hintStyle: GoogleFonts.inter(
                              color: arcxWhite.withValues(alpha: 0.2),
                              fontSize: 16,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              
              const Spacer(),
              
              // Continue Button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const PhoneOtpScreen()),
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: arcxWhite,
                    foregroundColor: arcxBlack,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: Text(
                    'Send SMS Code',
                    style: GoogleFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
