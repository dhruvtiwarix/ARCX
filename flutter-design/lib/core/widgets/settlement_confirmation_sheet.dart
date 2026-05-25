import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/settlement_provider.dart';
import 'quote_countdown_ring.dart';
import 'arcx_pin_sheet.dart';

class SettlementConfirmationSheet extends ConsumerWidget {
  final String action; // 'WITHDRAW' or 'TRANSFER'
  final String amountDisplay;
  final String? recipient;
  final Future<Map<String, dynamic>?> Function() onConfirm;

  const SettlementConfirmationSheet({
    super.key,
    required this.action,
    required this.amountDisplay,
    this.recipient,
    required this.onConfirm,
  });

  static Future<bool> show(
    BuildContext context,
    WidgetRef ref, {
    required String action,
    required String amountDisplay,
    String? recipient,
    required Future<Map<String, dynamic>?> Function() onConfirm,
  }) async {
    final notifier = ref.read(settlementProvider.notifier);
    
    // 1. Request Quote
    final bool quoteSuccess = await notifier.requestQuote(action);
    if (!quoteSuccess) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to get a price quote. Try again.')),
        );
      }
      return false;
    }

    // 2. Show Confirmation Sheet
    if (!context.mounted) return false;
    final bool? result = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => SettlementConfirmationSheet(
        action: action,
        amountDisplay: amountDisplay,
        recipient: recipient,
        onConfirm: onConfirm,
      ),
    );

    return result ?? false;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(settlementProvider);
    final bool isWithdraw = action == 'WITHDRAW';

    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF1C1C1E),
        borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
      ),
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
        top: 12,
        left: 24,
        right: 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 24),
          
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isWithdraw ? 'Confirm Withdrawal' : 'Confirm Transfer',
                    style: GoogleFonts.inter(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Prices are locked for 30 seconds',
                    style: GoogleFonts.inter(
                      color: const Color(0xFF8E8E93),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              QuoteCountdownRing(secondsRemaining: state.secondsRemaining),
            ],
          ),
          
          const SizedBox(height: 32),
          
          // Transaction Summary Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              children: [
                _buildRow('Amount', amountDisplay, isBold: true),
                if (recipient != null) ...[
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Divider(color: Colors.white10),
                  ),
                  _buildRow('To', recipient!),
                ],
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Divider(color: Colors.white10),
                ),
                _buildRow(
                  'Locked Rate', 
                  '₹${(isWithdraw ? state.lockedBidInr : state.lockedAskInr).toStringAsFixed(2)}',
                  subtitle: 'per ARCX',
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Divider(color: Colors.white10),
                ),
                _buildRow('Network Fee', '₹0.00', color: const Color(0xFF30D158)),
              ],
            ),
          ),
          
          const SizedBox(height: 32),
          
          // Action Button
          SizedBox(
            width: double.infinity,
            height: 56,
            child: ElevatedButton(
              onPressed: state.isQuoteValid ? () async {
                // Show PIN entry
                final String? pin = await ArcxPinSheet.show(
                  context,
                  amount: amountDisplay,
                  recipient: recipient ?? 'My Bank Account',
                );

                if (pin != null && context.mounted) {
                  final result = await onConfirm();
                  if (result != null && context.mounted) {
                    Navigator.pop(context, true);
                  }
                }
              } : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF30D158),
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                elevation: 0,
              ),
              child: Text(
                'Confirm & Execute',
                style: GoogleFonts.inter(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          
          const SizedBox(height: 12),
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(
              'Cancel',
              style: GoogleFonts.inter(
                color: const Color(0xFF8E8E93),
                fontSize: 15,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRow(String label, String value, {bool isBold = false, Color? color, String? subtitle}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: GoogleFonts.inter(
                color: const Color(0xFF8E8E93),
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle,
                style: GoogleFonts.inter(
                  color: const Color(0xFF8E8E93).withValues(alpha: 0.5),
                  fontSize: 10,
                  fontWeight: FontWeight.w400,
                ),
              ),
          ],
        ),
        Text(
          value,
          style: GoogleFonts.inter(
            color: color ?? Colors.white,
            fontSize: isBold ? 17 : 15,
            fontWeight: isBold ? FontWeight.w700 : FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
