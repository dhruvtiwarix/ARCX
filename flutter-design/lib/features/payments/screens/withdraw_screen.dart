import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/widgets/settlement_confirmation_sheet.dart';
import '../../../core/providers/settlement_provider.dart';
import '../../../core/providers/wallet_provider.dart';

class WithdrawScreen extends ConsumerStatefulWidget {
  const WithdrawScreen({super.key});

  @override
  ConsumerState<WithdrawScreen> createState() => _WithdrawScreenState();
}

class _WithdrawScreenState extends ConsumerState<WithdrawScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxRed = Color(0xFFFF453A); // iOS Red for withdrawal

  String _amount = '0';

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

  @override
  Widget build(BuildContext context) {
    final walletData = ref.watch(walletProvider).data;
    final double maxArcx = double.tryParse(walletData?['arcx_balance'] ?? '0') ?? 0;
    final double parsedAmount = double.tryParse(_amount) ?? 0;
    
    // We display INR to the user, but the backend thinks in ARCX units
    // For withdrawal, we'll estimate the ARCX needed based on the current NAV
    final double estimatedInr = parsedAmount; 

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(CupertinoIcons.back, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'Withdraw Funds',
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 24),

            // Amount Display
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                children: [
                  Text(
                    '₹$_amount',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 48,
                      fontWeight: FontWeight.w300,
                      letterSpacing: -2,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Available: ${maxArcx.toStringAsFixed(2)} ARCX',
                    style: GoogleFonts.inter(
                      color: textMuted,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            
            const Spacer(),

            // Info Box
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: GlassContainer(
                borderRadius: 16,
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    const Icon(CupertinoIcons.info_circle, color: textMuted, size: 18),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Funds will be settled to your linked bank account via instant settlement.',
                        style: GoogleFonts.inter(
                          color: textMuted,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

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

            // Withdraw Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: parsedAmount > 0 ? () => _handleWithdraw(context) : null,
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
                    'Review Withdrawal',
                    style: GoogleFonts.inter(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.4,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _handleWithdraw(BuildContext context) async {
    // 1. Show the confirmation sheet with price locking
    final bool success = await SettlementConfirmationSheet.show(
      context,
      ref,
      action: 'WITHDRAW',
      amountDisplay: '₹$_amount',
      onConfirm: () async {
        final amount = double.tryParse(_amount) ?? 0;
        // Use the .notifier to call the execution method
        return await ref.read(settlementProvider.notifier).executeWithdraw(amount);
      },
    );

    if (success && mounted) {
      // Refresh wallet after success
      ref.read(walletProvider.notifier).refresh();
      Navigator.pop(context);
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Withdrawal successful!'),
          backgroundColor: Color(0xFF30D158),
        ),
      );
    }
  }

  Widget _buildNumRow(List<String> keys) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: keys.map<Widget>((key) {
        return GestureDetector(
          onTap: () => _onKeyTap(key),
          behavior: HitTestBehavior.opaque,
          child: Container(
            decoration: BoxDecoration(
              color: surfaceColor,
              shape: BoxShape.circle,
            ),
            child: SizedBox(
              width: 64,
              height: 64,
              child: Center(
                child: key == '⌫'
                    ? Icon(CupertinoIcons.delete_left, color: Colors.white.withValues(alpha: 0.6), size: 24)
                    : Text(
                        key,
                        style: GoogleFonts.inter(
                          color: Colors.white,
                          fontSize: 28,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}
