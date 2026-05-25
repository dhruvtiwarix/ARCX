import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../dashboard/screens/dashboard_screen.dart';
import '../../../core/network/api_service.dart';

class OtpScreen extends StatefulWidget {
  final String email;
  
  const OtpScreen({super.key, required this.email});

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  // iOS Minimal Dark Mode Palette
  static const Color arcxBlack = Color(0xFF000000);
  static const Color arcxWhite = Color(0xFFFFFFFF);
  static const Color arcxGray = Color(0xFF1C1C1E);
  static const Color arcxGold = Color(0xFFFFD60A);

  final List<TextEditingController> _controllers = List.generate(6, (index) => TextEditingController());
  final List<FocusNode> _focusNodes = List.generate(6, (index) => FocusNode());
  final ApiService _apiService = ApiService();
  bool _isLoading = false;

  void _verifyOtp() async {
    final otp = _controllers.map((c) => c.text).join();
    if (otp.length < 6) return;

    setState(() => _isLoading = true);

    final success = await _apiService.verifyOtp(widget.email, otp);

    setState(() => _isLoading = false);

    if (success && mounted) {
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (context) => const DashboardScreen()),
        (route) => false,
      );
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid or expired OTP. Please try again.')),
      );
      // Clear OTP
      for (var c in _controllers) {
        c.clear();
      }
      _focusNodes[0].requestFocus();
    }
  }

  void _onOtpChanged(String value, int index) {
    if (value.isNotEmpty && index < 5) {
      _focusNodes[index + 1].requestFocus();
    }
    if (index == 5 && value.isNotEmpty) {
      // Auto verify when 6th digit is entered
      FocusScope.of(context).unfocus();
      _verifyOtp();
    }
  }

  @override
  void dispose() {
    for (var c in _controllers) c.dispose();
    for (var f in _focusNodes) f.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: arcxBlack,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const SizedBox(height: 20),
                
                // 1. Back Button
                Align(
                  alignment: Alignment.centerLeft,
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: () => Navigator.pop(context),
                      borderRadius: BorderRadius.circular(20),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        child: const Icon(
                          CupertinoIcons.back,
                          color: arcxWhite,
                          size: 20,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 40),

                // 2. Header Icon & Text
                const Icon(CupertinoIcons.mail, color: arcxGold, size: 48),
                const SizedBox(height: 24),
                Text(
                  'Check your email',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.playfairDisplay(
                    color: arcxWhite,
                    fontSize: 32,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'We sent a 6-digit secure code to\n${widget.email}',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.6),
                    fontSize: 14,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 40),

                // 3. OTP Input Fields
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: List<Widget>.generate(
                    6,
                    (index) => SizedBox(
                      width: 45,
                      child: Container(
                        decoration: BoxDecoration(
                          color: arcxGray,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: arcxWhite.withValues(alpha: 0.1)),
                        ),
                        child: TextField(
                          controller: _controllers[index],
                          focusNode: _focusNodes[index],
                          onChanged: (val) => _onOtpChanged(val, index),
                          textAlign: TextAlign.center,
                          keyboardType: TextInputType.number,
                          maxLength: 1,
                          style: GoogleFonts.inter(
                            color: arcxWhite,
                            fontSize: 24,
                            fontWeight: FontWeight.w600,
                          ),
                          decoration: const InputDecoration(
                            counterText: '',
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(vertical: 16),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // 4. Verify Button
                ElevatedButton(
                  onPressed: _isLoading ? null : _verifyOtp,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: arcxWhite,
                    minimumSize: const Size(double.infinity, 56),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(color: arcxBlack, strokeWidth: 2),
                        )
                      : Text(
                          'Verify & Continue',
                          style: GoogleFonts.inter(
                            color: arcxBlack,
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -0.4,
                          ),
                        ),
                ),
                const SizedBox(height: 24),

                // 5. Resend Options
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      "Didn't receive it? ",
                      style: GoogleFonts.inter(
                        color: arcxWhite.withValues(alpha: 0.4),
                        fontSize: 14,
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        // Call _apiService.sendOtp again
                      },
                      child: Text(
                        "Resend Code",
                        style: GoogleFonts.inter(
                          color: arcxGold,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
