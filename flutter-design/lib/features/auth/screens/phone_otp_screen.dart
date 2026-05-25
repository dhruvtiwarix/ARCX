import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../payments/screens/deposit_screen.dart';

class PhoneOtpScreen extends StatelessWidget {
  const PhoneOtpScreen({super.key});

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
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: arcxGray,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: arcxWhite.withValues(alpha: 0.1)),
                ),
                child: const Icon(Icons.message_outlined, color: arcxWhite),
              ),
              const SizedBox(height: 32),
              
              Text(
                'Verify Phone',
                style: GoogleFonts.playfairDisplay(
                  color: arcxWhite,
                  fontSize: 32,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 12),
              RichText(
                text: TextSpan(
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.6),
                    fontSize: 14,
                    height: 1.5,
                  ),
                  children: [
                    const TextSpan(text: 'We sent a secure 6-digit code to '),
                    TextSpan(
                      text: '+91 98765 43210',
                      style: GoogleFonts.inter(
                        color: arcxWhite,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 48),
              
              // 6-digit OTP Row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: List.generate(6, (index) => _buildOtpBox()),
              ),
              const SizedBox(height: 32),
              
              // Resend Code
              Center(
                child: Text(
                  'Resend Code in 0:59',
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.4),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              
              const Spacer(),
              
              // Verify Button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    // Phone verified! Navigate to Deposit
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(builder: (context) => const DepositScreen()),
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
                    'Verify & Access Vault',
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

  Widget _buildOtpBox() {
    return Container(
      width: 48,
      height: 56,
      decoration: BoxDecoration(
        color: arcxGray,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: arcxWhite.withValues(alpha: 0.1)),
      ),
      child: Center(
        child: Text(
          '·', 
          style: GoogleFonts.inter(
            color: arcxWhite.withValues(alpha: 0.5),
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}
