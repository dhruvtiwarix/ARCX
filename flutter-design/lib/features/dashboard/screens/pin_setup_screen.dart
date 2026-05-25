import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/network/api_service.dart';

/// Full-screen PIN setup for first-time users.
class PinSetupScreen extends StatefulWidget {
  final VoidCallback onPinSet;

  const PinSetupScreen({super.key, required this.onPinSet});

  @override
  State<PinSetupScreen> createState() => _PinSetupScreenState();
}

class _PinSetupScreenState extends State<PinSetupScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color accentGold = Color(0xFFFFD60A);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  final ApiService _apiService = ApiService();
  String _pin = '';
  String _confirmPin = '';
  bool _isConfirming = false;
  bool _isSaving = false;
  bool _hasError = false;
  String _errorMessage = '';

  void _onKeyTap(String key) {
    if (_isSaving) return;

    setState(() {
      _hasError = false;
      _errorMessage = '';

      if (_isConfirming) {
        if (key == 'delete') {
          if (_confirmPin.isNotEmpty) _confirmPin = _confirmPin.substring(0, _confirmPin.length - 1);
        } else if (_confirmPin.length < 6) {
          _confirmPin += key;
        }
        if (_confirmPin.length == 6) _submitPin();
      } else {
        if (key == 'delete') {
          if (_pin.isNotEmpty) _pin = _pin.substring(0, _pin.length - 1);
        } else if (_pin.length < 6) {
          _pin += key;
        }
        if (_pin.length == 6) {
          Future.delayed(const Duration(milliseconds: 200), () {
            if (mounted) setState(() => _isConfirming = true);
          });
        }
      }
    });
  }

  Future<void> _submitPin() async {
    if (_pin != _confirmPin) {
      setState(() {
        _hasError = true;
        _errorMessage = 'PINs do not match. Try again.';
        _confirmPin = '';
        _isConfirming = false;
        _pin = '';
      });
      return;
    }

    setState(() => _isSaving = true);

    final success = await _apiService.setPin(_pin);

    if (success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('ARCX PIN set successfully!', style: GoogleFonts.inter()),
          backgroundColor: arcxGreen,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      );
      widget.onPinSet();
      Navigator.pop(context);
    } else if (mounted) {
      setState(() {
        _isSaving = false;
        _hasError = true;
        _errorMessage = 'Failed to set PIN. Try again.';
        _confirmPin = '';
        _pin = '';
        _isConfirming = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentPin = _isConfirming ? _confirmPin : _pin;
    final title = _isConfirming ? 'Confirm Your PIN' : 'Create ARCX PIN';
    final subtitle = _isConfirming
        ? 'Enter the same PIN again to confirm'
        : 'Set a 6-digit PIN to secure your transactions';

    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Column(
          children: [
            // App Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  GestureDetector(
                    onTap: () => Navigator.pop(context),
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E1E1E),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 18),
                    ),
                  ),
                ],
              ),
            ),

            const Spacer(flex: 2),

            // Shield Icon
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: accentGold.withValues(alpha: 0.1),
                shape: BoxShape.circle,
                border: Border.all(color: accentGold.withValues(alpha: 0.2)),
              ),
              child: Icon(Icons.lock_outline, color: accentGold, size: 32),
            ),
            const SizedBox(height: 24),

            Text(
              title,
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 26,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              subtitle,
              style: GoogleFonts.inter(color: textMuted, fontSize: 14),
              textAlign: TextAlign.center,
            ),
            if (_hasError) ...[
              const SizedBox(height: 8),
              Text(
                _errorMessage,
                style: GoogleFonts.inter(color: Colors.red, fontSize: 13, fontWeight: FontWeight.w500),
              ),
            ],
            const SizedBox(height: 40),

            // PIN Dots
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(6, (index) {
                final isFilled = index < currentPin.length;
                return AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  margin: const EdgeInsets.symmetric(horizontal: 8),
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _hasError
                        ? Colors.red.withValues(alpha: 0.3)
                        : isFilled
                            ? accentGold
                            : Colors.white.withValues(alpha: 0.15),
                    border: Border.all(
                      color: _hasError
                          ? Colors.red.withValues(alpha: 0.5)
                          : Colors.white.withValues(alpha: 0.1),
                    ),
                  ),
                );
              }),
            ),

            const Spacer(flex: 1),

            // Number Pad
            _buildNumberPad(),
            const SizedBox(height: 32),
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
