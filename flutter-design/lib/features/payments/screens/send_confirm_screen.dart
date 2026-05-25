import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/widgets/settlement_confirmation_sheet.dart';
import '../../../core/providers/settlement_provider.dart';
import '../../../core/providers/wallet_provider.dart';
import '../../dashboard/screens/dashboard_screen.dart';

class SendConfirmScreen extends ConsumerStatefulWidget {
  final String recipientName;
  final String recipientId;

  const SendConfirmScreen({
    super.key,
    required this.recipientName,
    required this.recipientId,
  });

  @override
  ConsumerState<SendConfirmScreen> createState() => _SendConfirmScreenState();
}

class _SendConfirmScreenState extends ConsumerState<SendConfirmScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  String _amount = '0';
  bool _showSuccess = false;

  void _onKeyTap(String key) {
    setState(() {
      if (key == '⌫') {
        if (_amount.length > 1) {
          _amount = _amount.substring(0, _amount.length - 1);
        } else {
          _amount = '0';
        }
      } else if (key == '.') {
        if (!_amount.contains('.')) {
          _amount += '.';
        }
      } else {
        if (_amount == '0') {
          _amount = key;
        } else {
          _amount += key;
        }
      }
    });
  }

  void _sendMoney() async {
    final double parsedAmount = double.tryParse(_amount) ?? 0;
    
    // Use the 30-second locked quote flow
    final bool success = await SettlementConfirmationSheet.show(
      context,
      ref,
      action: 'TRANSFER',
      amountDisplay: '$_amount ARCX',
      recipient: widget.recipientName,
      onConfirm: () async {
        // Here we'd normally look up the email from the ID, 
        // for now we'll assume the ID is the email or look it up.
        // Mocking the email as 'recipient@arcx.io' for the demo
        return await ref.read(settlementProvider.notifier).executeSend(
          'user@arcx.io', 
          parsedAmount,
        );
      },
    );

    if (success && mounted) {
      ref.read(walletProvider.notifier).refresh();
      setState(() => _showSuccess = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_showSuccess) return _buildSuccessView();

    final double parsedAmount = double.tryParse(_amount) ?? 0;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 16),

            // Recipient Info
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: surfaceColor,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
              child: Center(
                child: Text(
                  widget.recipientName.split(' ').map((e) => e[0]).join(),
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(
              widget.recipientName,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              widget.recipientId,
              style: GoogleFonts.inter(color: textMuted, fontSize: 13),
            ),
            const SizedBox(height: 40),

            // Amount
            Text(
              '$_amount ARCX',
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 40,
                fontWeight: FontWeight.w600,
                letterSpacing: -1,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '≈ ₹${(parsedAmount * 83).toStringAsFixed(0)}',
              style: GoogleFonts.inter(
                color: textMuted,
                fontSize: 14,
              ),
            ),

            const Spacer(),

            // Numpad
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                children: [
                  _buildNumRow(['1', '2', '3']),
                  const SizedBox(height: 12),
                  _buildNumRow(['4', '5', '6']),
                  const SizedBox(height: 12),
                  _buildNumRow(['7', '8', '9']),
                  const SizedBox(height: 12),
                  _buildNumRow(['.', '0', '⌫']),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Send Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: parsedAmount > 0 ? _sendMoney : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    disabledBackgroundColor: Colors.white.withValues(alpha: 0.1),
                    foregroundColor: Colors.black,
                    disabledForegroundColor: textMuted,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: Text(
                    'Send $_amount ARCX',
                    style: GoogleFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  // Success View (replaces entire screen)
  Widget _buildSuccessView() {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(flex: 2),

              // Animated Check
              TweenAnimationBuilder<double>(
                tween: Tween(begin: 0.0, end: 1.0),
                duration: const Duration(milliseconds: 600),
                curve: Curves.elasticOut,
                builder: (context, value, child) {
                  return Transform.scale(
                    scale: value,
                    child: Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        color: arcxGreen.withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(CupertinoIcons.checkmark_alt, color: arcxGreen, size: 56),
                    ),
                  );
                },
              ),
              const SizedBox(height: 32),

              Text(
                'Sent Successfully',
                style: GoogleFonts.playfairDisplay(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '$_amount ARCX sent to ${widget.recipientName}',
                style: GoogleFonts.inter(color: textMuted, fontSize: 14),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 48),

              // Receipt
              GlassContainer(
                borderRadius: 24,
                padding: const EdgeInsets.all(24),
                blur: 20,
                opacity: 0.08,
                child: Column(
                  children: [
                    _buildRow('To', widget.recipientName),
                    const SizedBox(height: 16),
                    Divider(color: Colors.white.withValues(alpha: 0.05)),
                    const SizedBox(height: 16),
                    _buildRow('ARCX ID', widget.recipientId),
                    const SizedBox(height: 16),
                    Divider(color: Colors.white.withValues(alpha: 0.05)),
                    const SizedBox(height: 16),
                    _buildRow('Amount', '$_amount ARCX'),
                    const SizedBox(height: 16),
                    Divider(color: Colors.white.withValues(alpha: 0.05)),
                    const SizedBox(height: 16),
                    _buildRow('Status', 'Settled', valueColor: arcxGreen),
                  ],
                ),
              ),

              const Spacer(flex: 3),

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
                    style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600),
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

  Widget _buildRow(String label, String value, {Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: GoogleFonts.inter(color: textMuted, fontSize: 14)),
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

  Widget _buildNumRow(List<String> keys) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: keys.map((key) {
        return GestureDetector(
          onTap: () => _onKeyTap(key),
          behavior: HitTestBehavior.opaque,
          child: SizedBox(
            width: 80,
            height: 56,
            child: Center(
              child: key == '⌫'
                  ? Icon(CupertinoIcons.delete_left, color: Colors.white.withValues(alpha: 0.6), size: 22)
                  : Text(
                      key,
                      style: GoogleFonts.inter(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
