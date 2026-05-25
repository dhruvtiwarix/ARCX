import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/glass_container.dart';
import '../../dashboard/screens/dashboard_screen.dart';

class LockScreen extends StatefulWidget {
  final VoidCallback? onUnlock;
  final Future<bool> Function()? onBiometricRequested;

  const LockScreen({super.key, this.onUnlock, this.onBiometricRequested});

  @override
  State<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends State<LockScreen> {
  static const Color arcxBlack = Color(0xFF000000);
  static const Color arcxWhite = Color(0xFFFFFFFF);
  // static const Color arcxGray = Color(0xFF1C1C1E);
  static const Color arcxRed = Color(0xFFFF3B30);

  String _pin = '';
  bool _isError = false;
  static const String _correctPin = '1234'; // Mock PIN

  void _onKeyTap(String value) {
    if (_pin.length < 4) {
      setState(() {
        _isError = false;
        _pin += value;
      });

      if (_pin.length == 4) {
        _validatePin();
      }
    }
  }

  void _onDelete() {
    if (_pin.isNotEmpty) {
      setState(() {
        _isError = false;
        _pin = _pin.substring(0, _pin.length - 1);
      });
    }
  }

  void _validatePin() {
    if (_pin == _correctPin) {
      if (widget.onUnlock != null) {
        widget.onUnlock!();
      } else {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => const DashboardScreen()),
        );
      }
    } else {
      setState(() {
        _isError = true;
        _pin = '';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: arcxBlack,
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(flex: 2),

            // Logo / Branding
            Text(
              'ARCX',
              style: GoogleFonts.playfairDisplay(
                color: arcxWhite,
                fontSize: 36,
                fontWeight: FontWeight.w700,
                letterSpacing: 4,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Enter your PIN',
              style: GoogleFonts.inter(
                color: arcxWhite.withValues(alpha: 0.5),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 40),

            // PIN Dots
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(4, (index) {
                final bool isFilled = index < _pin.length;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.symmetric(horizontal: 12),
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _isError
                        ? arcxRed
                        : isFilled
                            ? arcxWhite
                            : Colors.transparent,
                    border: Border.all(
                      color: _isError
                          ? arcxRed
                          : arcxWhite.withValues(alpha: 0.3),
                      width: 1.5,
                    ),
                  ),
                );
              }),
            ),

            if (_isError) ...[
              const SizedBox(height: 16),
              Text(
                'Incorrect PIN. Try again.',
                style: GoogleFonts.inter(
                  color: arcxRed,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],

            const Spacer(flex: 2),

            // Numpad
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 48),
              child: Column(
                children: [
                  _buildNumRow(['1', '2', '3']),
                  const SizedBox(height: 16),
                  _buildNumRow(['4', '5', '6']),
                  const SizedBox(height: 16),
                  _buildNumRow(['7', '8', '9']),
                  const SizedBox(height: 16),
                  _buildBottomRow(),
                ],
              ),
            ),

            const Spacer(flex: 1),
          ],
        ),
      ),
    );
  }

  Widget _buildNumRow(List<String> nums) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: nums.map((n) => _buildNumKey(n)).toList(),
    );
  }

  Widget _buildBottomRow() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        // Biometric button
        SizedBox(
          width: 72,
          height: 72,
          child: widget.onBiometricRequested != null
              ? IconButton(
                  onPressed: () async {
                    final success = await widget.onBiometricRequested!();
                    if (success && widget.onUnlock != null) {
                      widget.onUnlock!();
                    }
                  },
                  icon: const Icon(CupertinoIcons.person_crop_circle, color: arcxWhite, size: 32),
                )
              : const SizedBox.shrink(),
        ),
        _buildNumKey('0'),
        // Delete button
        SizedBox(
          width: 72,
          height: 72,
          child: IconButton(
            onPressed: _onDelete,
            icon: Icon(CupertinoIcons.delete_left, color: arcxWhite.withValues(alpha: 0.6), size: 24),
          ),
        ),
      ],
    );
  }

  Widget _buildNumKey(String num) {
    return GestureDetector(
      onTap: () => _onKeyTap(num),
      child: GlassContainer(
        borderRadius: 36,
        blur: 15,
        opacity: 0.06,
        child: SizedBox(
          width: 72,
          height: 72,
          child: Center(
            child: Text(
              num,
              style: GoogleFonts.inter(
                color: arcxWhite,
                fontSize: 28,
                fontWeight: FontWeight.w400,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
