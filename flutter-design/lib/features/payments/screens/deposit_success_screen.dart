import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/glass_container.dart';
import '../../dashboard/screens/dashboard_screen.dart';

class DepositSuccessScreen extends StatefulWidget {
  final String amount;
  final String arcxValue;

  const DepositSuccessScreen({
    super.key,
    required this.amount,
    required this.arcxValue,
  });

  @override
  State<DepositSuccessScreen> createState() => _DepositSuccessScreenState();
}

class _DepositSuccessScreenState extends State<DepositSuccessScreen>
    with SingleTickerProviderStateMixin {
  // iOS Minimal Dark Mode Palette
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color arcxGreen = Color(0xFF30D158); // iOS Green
  static const Color textMuted = Color(0xFF8E8E93);

  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );

    _scaleAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.elasticOut),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.3, 1.0, curve: Curves.easeOut),
      ),
    );

    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(flex: 2),

              // Animated Check Mark
              AnimatedBuilder(
                animation: _controller,
                builder: (context, child) {
                  return Transform.scale(
                    scale: _scaleAnimation.value,
                    child: Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        color: arcxGreen.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        CupertinoIcons.checkmark_alt,
                        color: arcxGreen,
                        size: 56,
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(height: 32),

              // Success Text
              FadeTransition(
                opacity: _fadeAnimation,
                child: Column(
                  children: [
                    Text(
                      'Deposit Successful',
                      style: GoogleFonts.playfairDisplay(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '₹${widget.amount} has been added to your vault',
                      style: GoogleFonts.inter(
                        color: textMuted,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 48),

              // Receipt Card
              FadeTransition(
                opacity: _fadeAnimation,
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: surfaceColor,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.05),
                      width: 1,
                    ),
                  ),
                  child: Column(
                    children: [
                      _buildReceiptRow('Amount', '₹${widget.amount}'),
                      const SizedBox(height: 16),
                      Divider(color: Colors.white.withValues(alpha: 0.05)),
                      const SizedBox(height: 16),
                      _buildReceiptRow('ARCX Received', '${widget.arcxValue} ARCX'),
                      const SizedBox(height: 16),
                      Divider(color: Colors.white.withValues(alpha: 0.05)),
                      const SizedBox(height: 16),
                      _buildReceiptRow('Rate', '1 ARCX ≈ ₹83.00'),
                      const SizedBox(height: 16),
                      Divider(color: Colors.white.withValues(alpha: 0.05)),
                      const SizedBox(height: 16),
                      _buildReceiptRow('Status', 'Confirmed', valueColor: arcxGreen),
                    ],
                  ),
                ),
              ),

              const Spacer(flex: 3),

              // Return to Dashboard
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pushAndRemoveUntil(
                      context,
                      MaterialPageRoute(builder: (context) => const DashboardScreen()),
                      (route) => false,
                    );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: Text(
                    'Back to Dashboard',
                    style: GoogleFonts.inter(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.4,
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

  Widget _buildReceiptRow(String label, String value, {Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: GoogleFonts.inter(
            color: textMuted,
            fontSize: 14,
          ),
        ),
        Text(
          value,
          style: GoogleFonts.inter(
            color: valueColor ?? Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
