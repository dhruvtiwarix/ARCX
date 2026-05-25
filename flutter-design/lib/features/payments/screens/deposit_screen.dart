import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/widgets/arcx_pin_sheet.dart';
import '../../../core/network/api_service.dart';
import '../../../core/providers/treasury_provider.dart';
import 'deposit_success_screen.dart';

class DepositScreen extends ConsumerStatefulWidget {
  const DepositScreen({super.key});

  @override
  ConsumerState<DepositScreen> createState() => _DepositScreenState();
}

class _DepositScreenState extends ConsumerState<DepositScreen> {
  // iOS Minimal Dark Mode Palette
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color cardColor = Color(0xFF1C1C1E);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158); // iOS Green

  String _amount = '0';
  int _selectedMethod = 0; // 0 = UPI, 1 = Bank Transfer

  @override
  void initState() {
    super.initState();
    // Fetch live ARCX price from oracle
    Future.microtask(() => ref.read(treasuryProvider.notifier).loadTreasury());
  }

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
    final treasury = ref.watch(treasuryProvider);
    final double parsedAmount = double.tryParse(_amount) ?? 0;

    // Use live NAV from oracle, fallback to 83
    final double arcxPriceInr = treasury.data?['arcx_price_inr'] != null
        ? double.tryParse(treasury.data!['arcx_price_inr'].toString()) ?? 83.0
        : 83.0;
    final double arcxValue = parsedAmount > 0 ? parsedAmount / arcxPriceInr : 0;

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
          'Add Funds',
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverFillRemaining(
              hasScrollBody: false,
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
                    '≈ ${arcxValue.toStringAsFixed(2)} ARCX',
                    style: GoogleFonts.inter(
                      color: arcxGreen,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Quick Amount Chips
            SizedBox(
              height: 40,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 24),
                children: [
                  _buildQuickChip('₹500'),
                  const SizedBox(width: 10),
                  _buildQuickChip('₹1,000'),
                  const SizedBox(width: 10),
                  _buildQuickChip('₹5,000'),
                  const SizedBox(width: 10),
                  _buildQuickChip('₹10,000'),
                  const SizedBox(width: 10),
                  _buildQuickChip('₹20,000'),
                  ],
                ),
              ),
              const SizedBox(height: 24),

            // Payment Method Selection
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Payment Method',
                    style: GoogleFonts.inter(
                      color: textMuted,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: _buildPaymentMethod(0, CupertinoIcons.qrcode, 'UPI')),
                      const SizedBox(width: 12),
                      Expanded(child: _buildPaymentMethod(1, CupertinoIcons.building_2_fill, 'Bank Transfer')),
                    ],
                  ),
                ],
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

            // Deposit Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: parsedAmount > 0
                      ? () async {
                          final String? pin = await ArcxPinSheet.show(
                            context,
                            amount: '₹$_amount',
                            recipient: 'ARCX Wallet',
                          );
                          if (pin != null && mounted) {
                            // Show loading dialog
                            showDialog(
                              context: context,
                              barrierDismissible: false,
                              builder: (context) => const Center(
                                child: CircularProgressIndicator(color: Colors.white),
                              ),
                            );

                            final apiService = ApiService();
                            final result = await apiService.depositInr(parsedAmount, pin: pin);
                            
                            // Remove loading dialog
                            if (mounted) Navigator.pop(context);

                            if (result != null && mounted) {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => DepositSuccessScreen(
                                    amount: _amount,
                                    arcxValue: double.parse(result['arcx_received'].toString()).toStringAsFixed(2),
                                  ),
                                ),
                              );
                            } else if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Deposit failed. Please try again.')),
                              );
                            }
                          }
                        }
                      : null,
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
                    'Deposit ₹$_amount',
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
          ],
        ),
      ),
    );
  }

  Widget _buildQuickChip(String label) {
    return GestureDetector(
      onTap: () {
        setState(() {
          _amount = label.replaceAll('₹', '').replaceAll(',', '');
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.05),
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildPaymentMethod(int index, IconData icon, String label) {
    final bool isSelected = _selectedMethod == index;
    return GestureDetector(
      onTap: () => setState(() => _selectedMethod = index),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected ? surfaceColor.withValues(alpha: 0.8) : surfaceColor,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? Colors.white.withValues(alpha: 0.3) : Colors.white.withValues(alpha: 0.05),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: Colors.white, size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
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
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.05),
                width: 1,
              ),
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
