import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/network/api_service.dart';

/// Modal bottom sheet for ARCX PIN verification before financial actions.
/// Returns `true` if PIN is verified, `false` or `null` if dismissed.
Future<bool?> showPinVerificationSheet(BuildContext context) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => const _PinVerificationSheet(),
  );
}

class _PinVerificationSheet extends StatefulWidget {
  const _PinVerificationSheet();

  @override
  State<_PinVerificationSheet> createState() => _PinVerificationSheetState();
}

class _PinVerificationSheetState extends State<_PinVerificationSheet>
    with SingleTickerProviderStateMixin {
  static const Color bgColor = Color(0xFF1E1E1E);
  static const Color accentGold = Color(0xFFFFD54F);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF34C759);

  final ApiService _apiService = ApiService();
  String _pin = '';
  bool _isVerifying = false;
  bool _hasError = false;

  late AnimationController _shakeController;
  late Animation<double> _shakeAnimation;

  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _shakeAnimation = Tween(begin: 0.0, end: 10.0)
        .chain(CurveTween(curve: Curves.elasticIn))
        .animate(_shakeController);
  }

  @override
  void dispose() {
    _shakeController.dispose();
    super.dispose();
  }

  void _onKeyTap(String key) {
    if (_isVerifying) return;

    setState(() {
      _hasError = false;
      if (key == 'delete') {
        if (_pin.isNotEmpty) {
          _pin = _pin.substring(0, _pin.length - 1);
        }
      } else if (_pin.length < 6) {
        _pin += key;
      }
    });

    if (_pin.length == 6) {
      _verifyPin();
    }
  }

  Future<void> _verifyPin() async {
    setState(() => _isVerifying = true);

    final isValid = await _apiService.verifyPin(_pin);

    if (isValid && mounted) {
      Navigator.pop(context, true);
    } else if (mounted) {
      _shakeController.forward(from: 0);
      setState(() {
        _hasError = true;
        _isVerifying = false;
        _pin = '';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Handle
            const SizedBox(height: 12),
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 28),

            // Title
            Icon(
              Icons.shield_outlined,
              color: accentGold.withValues(alpha: 0.7),
              size: 32,
            ),
            const SizedBox(height: 12),
            Text(
              'Enter ARCX PIN',
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _hasError ? 'Incorrect PIN. Try again.' : 'Enter your 6-digit transaction PIN',
              style: GoogleFonts.inter(
                color: _hasError ? Colors.red : textMuted,
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 32),

            // PIN Dots
            AnimatedBuilder(
              animation: _shakeAnimation,
              builder: (context, child) {
                return Transform.translate(
                  offset: Offset(_shakeAnimation.value * (_shakeController.status == AnimationStatus.forward ? 1 : -1), 0),
                  child: child,
                );
              },
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(6, (index) {
                  final isFilled = index < _pin.length;
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.symmetric(horizontal: 8),
                    width: 16,
                    height: 16,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _hasError
                          ? Colors.red.withValues(alpha: isFilled ? 1 : 0.3)
                          : isFilled
                              ? accentGold
                              : Colors.white.withValues(alpha: 0.15),
                      border: Border.all(
                        color: _hasError
                            ? Colors.red.withValues(alpha: 0.5)
                            : Colors.white.withValues(alpha: 0.1),
                        width: 1,
                      ),
                    ),
                  );
                }),
              ),
            ),
            const SizedBox(height: 40),

            // Number Pad
            _buildNumberPad(),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildNumberPad() {
    final keys = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      ['', '0', 'delete'],
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Column(
        children: keys.map((row) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: row.map((key) {
                if (key.isEmpty) return const SizedBox(width: 72, height: 56);
                return _buildKey(key);
              }).toList(),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildKey(String key) {
    final isDelete = key == 'delete';

    return GestureDetector(
      onTap: () => _onKeyTap(key),
      child: Container(
        width: 72,
        height: 56,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(16),
        ),
        alignment: Alignment.center,
        child: isDelete
            ? Icon(Icons.backspace_outlined, color: Colors.white.withValues(alpha: 0.7), size: 22)
            : Text(
                key,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 24,
                  fontWeight: FontWeight.w500,
                ),
              ),
      ),
    );
  }
}
