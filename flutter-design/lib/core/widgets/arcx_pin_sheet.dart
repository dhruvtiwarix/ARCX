import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// A UPI-style ARCX PIN overlay that slides up from the bottom.
/// Returns `true` if PIN is correct, `false` if cancelled.
class ArcxPinSheet extends StatefulWidget {
  final String amount;
  final String recipient;

  const ArcxPinSheet({
    super.key,
    required this.amount,
    required this.recipient,
  });

  /// Show the ARCX PIN sheet and return the entered PIN if successful, null if cancelled/failed
  static Future<String?> show(BuildContext context, {required String amount, required String recipient}) async {
    final result = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      isDismissible: false,
      builder: (context) => ArcxPinSheet(amount: amount, recipient: recipient),
    );
    return result;
  }

  @override
  State<ArcxPinSheet> createState() => _ArcxPinSheetState();
}

class _ArcxPinSheetState extends State<ArcxPinSheet> with SingleTickerProviderStateMixin {
  static const Color bgColor = Color(0xFF0A0A0A);
  static const Color surfaceColor = Color(0xFF1E1E1E);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF34C759);
  static const Color arcxRed = Color(0xFFFF3B30);

  String _pin = '';
  bool _isError = false;
  bool _isSuccess = false;
  static const String _correctPin = '123456'; // Mock PIN (6 digits)

  late AnimationController _shakeController;
  late Animation<double> _shakeAnimation;

  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _shakeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _shakeController, curve: Curves.elasticIn),
    );
  }

  @override
  void dispose() {
    _shakeController.dispose();
    super.dispose();
  }

  void _onKeyTap(String value) {
    if (_pin.length < 6 && !_isSuccess) {
      setState(() {
        _isError = false;
        _pin += value;
      });

      if (_pin.length == 6) {
        _validatePin();
      }
    }
  }

  void _onDelete() {
    if (_pin.isNotEmpty && !_isSuccess) {
      setState(() {
        _isError = false;
        _pin = _pin.substring(0, _pin.length - 1);
      });
    }
  }

  void _validatePin() async {
    if (_pin == _correctPin) {
      setState(() => _isSuccess = true);
      await Future.delayed(const Duration(milliseconds: 800));
      if (mounted) Navigator.pop(context, _pin);
    } else {
      setState(() {
        _isError = true;
        _pin = '';
      });
      _shakeController.forward(from: 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(32)),
          border: Border(
            top: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(height: 12),
                // Drag Handle
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 24),

                // Header
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'ARCX PIN',
                          style: GoogleFonts.inter(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Authorize this payment',
                          style: GoogleFonts.inter(color: textMuted, fontSize: 13),
                        ),
                      ],
                    ),
                    GestureDetector(
                      onTap: () => Navigator.pop(context, false),
                      child: Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: surfaceColor,
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                        ),
                        child: const Icon(Icons.close, color: Colors.white, size: 18),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Transaction Summary
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: surfaceColor,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Sending to',
                            style: GoogleFonts.inter(color: textMuted, fontSize: 11),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            widget.recipient,
                            style: GoogleFonts.inter(
                              color: Colors.white,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        widget.amount,
                        style: GoogleFonts.inter(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 32),

                // PIN Dots
                AnimatedBuilder(
                  animation: _shakeAnimation,
                  builder: (context, child) {
                    final shake = _isError
                        ? (1 - _shakeAnimation.value) * 10 * (_shakeAnimation.value * 4 % 2 == 0 ? 1 : -1)
                        : 0.0;
                    return Transform.translate(
                      offset: Offset(shake, 0),
                      child: child,
                    );
                  },
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(6, (index) {
                      final bool isFilled = index < _pin.length;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 150),
                        margin: const EdgeInsets.symmetric(horizontal: 14),
                        width: isFilled ? 16 : 14,
                        height: isFilled ? 16 : 14,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _isSuccess
                              ? arcxGreen
                              : _isError
                                  ? arcxRed
                                  : isFilled
                                      ? Colors.white
                                      : Colors.transparent,
                          border: Border.all(
                            color: _isSuccess
                                ? arcxGreen
                                : _isError
                                    ? arcxRed
                                    : Colors.white.withValues(alpha: 0.3),
                            width: 1.5,
                          ),
                        ),
                      );
                    }),
                  ),
                ),

                if (_isError) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Wrong PIN. Try again.',
                    style: GoogleFonts.inter(color: arcxRed, fontSize: 13, fontWeight: FontWeight.w500),
                  ),
                ],

                if (_isSuccess) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Authorized ✓',
                    style: GoogleFonts.inter(color: arcxGreen, fontSize: 13, fontWeight: FontWeight.w600),
                  ),
                ],

                const SizedBox(height: 32),

                // Numpad
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Column(
                    children: [
                      _buildRow(['1', '2', '3']),
                      const SizedBox(height: 12),
                      _buildRow(['4', '5', '6']),
                      const SizedBox(height: 12),
                      _buildRow(['7', '8', '9']),
                      const SizedBox(height: 12),
                      _buildBottomRow(),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRow(List<String> nums) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: nums.map((n) => _buildKey(n)).toList(),
    );
  }

  Widget _buildBottomRow() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        // Empty spacer
        const SizedBox(width: 72, height: 56),
        _buildKey('0'),
        // Backspace
        GestureDetector(
          onTap: _onDelete,
          child: SizedBox(
            width: 72,
            height: 56,
            child: Center(
              child: Icon(Icons.backspace_outlined, color: Colors.white.withValues(alpha: 0.6), size: 22),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildKey(String num) {
    return GestureDetector(
      onTap: () => _onKeyTap(num),
      child: Container(
        width: 72,
        height: 56,
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: 0.03)),
        ),
        child: Center(
          child: Text(
            num,
            style: GoogleFonts.inter(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}
