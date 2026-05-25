import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class BalanceCard extends StatelessWidget {
  final double balance;
  final double yieldPercentage;

  const BalanceCard({
    super.key,
    required this.balance,
    required this.yieldPercentage,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24.0),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(16.0), // Sharper, elegant corners
        border: Border.all(
          color: Colors.white.withOpacity(0.05), // Subtle inner border instead of glow
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Total Balance',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const Spacer(),
              // A small luxury accent
              const Icon(Icons.account_balance_wallet, color: AppTheme.primary, size: 20),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                'A\$${balance.toStringAsFixed(2)}', 
                // Using the Serif font (Playfair Display) for the large number
                style: Theme.of(context).textTheme.displayLarge?.copyWith(
                  fontSize: 36,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.positiveYield.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.arrow_upward,
                      color: AppTheme.positiveYield,
                      size: 14,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '+$yieldPercentage%',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppTheme.positiveYield,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
