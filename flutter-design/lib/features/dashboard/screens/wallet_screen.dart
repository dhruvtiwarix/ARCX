import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/network/api_service.dart';
import '../../../core/providers/wallet_provider.dart';

class WalletScreen extends ConsumerStatefulWidget {
  const WalletScreen({super.key});

  @override
  ConsumerState<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends ConsumerState<WalletScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color accentGold = Color(0xFFFFD60A);
  static const Color accentPurple = Color(0xFFA855F7);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  // Global state getters
  Map<String, dynamic>? get _walletData => ref.watch(walletProvider).data;
  bool get _isLoading => ref.watch(walletProvider).isLoading;

  @override
  void initState() {
    super.initState();
  }

  Future<void> _refreshData() async {
    await ref.read(walletProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    final wallet = _walletData;

    return RefreshIndicator(
      onRefresh: _refreshData,
      color: accentGold,
      backgroundColor: surfaceColor,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 16),
            Text(
              'Wallet',
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Your ARCX balance & assets',
              style: GoogleFonts.inter(color: textMuted, fontSize: 14),
            ),
            const SizedBox(height: 24),

            // ARCX Balance Card
            _buildBalanceCard(wallet),
            const SizedBox(height: 24),

            // Stats Row
            if (!_isLoading && wallet != null) ...[
              _buildStatRow(wallet),
              const SizedBox(height: 32),
            ],

            _buildSectionTitle('LINKED ACCOUNTS'),
            const SizedBox(height: 8),

            if (_isLoading)
              _buildLoadingSkeleton()
            else
              _buildGlassSection(_buildLinkedAccountsList(wallet)),

            const SizedBox(height: 32),
            _buildSectionTitle('CARDS'),
            const SizedBox(height: 8),
            _buildGlassSection([
              _buildCardTile(),
            ]),

            const SizedBox(height: 32),

            // Add Account Button
            SizedBox(
              width: double.infinity,
              height: 56,
              child: OutlinedButton.icon(
                onPressed: () {},
                icon: const Icon(CupertinoIcons.add, color: Colors.white),
                label: Text(
                  'Link New Account',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 100),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(left: 4),
        child: Text(
          title,
          style: GoogleFonts.inter(
            color: textMuted,
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.5,
          ),
        ),
      ),
    );
  }

  Widget _buildGlassSection(List<Widget> children) {
    return GlassContainer(
      borderRadius: 20,
      padding: const EdgeInsets.all(8),
      blur: 20,
      opacity: 0.06,
      child: Column(
        children: [
          for (int i = 0; i < children.length; i++) ...[
            children[i],
            if (i < children.length - 1)
              Divider(
                height: 0.5,
                color: Colors.white.withValues(alpha: 0.05),
                indent: 50,
                endIndent: 16,
              ),
          ],
        ],
      ),
    );
  }

  Widget _buildBalanceCard(Map<String, dynamic>? wallet) {
    final arcxBalance = _isLoading ? '---' : (wallet?['arcx_balance'] ?? '0');
    final inrValue = _isLoading ? '---' : (wallet?['current_value_inr'] ?? '0');

    return GlassContainer(
      borderRadius: 20,
      padding: const EdgeInsets.all(20),
      blur: 25,
      opacity: 0.1,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [accentGold, accentPurple.withValues(alpha: 0.6)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  'ACX',
                  style: GoogleFonts.playfairDisplay(
                    color: Colors.black,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text(
                'ARCX Balance',
                style: GoogleFonts.inter(
                  color: textMuted,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                _isLoading ? '---' : NumberFormat('#,##0.00').format(double.tryParse(arcxBalance.toString()) ?? 0),
                style: GoogleFonts.playfairDisplay(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: 8),
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Text(
                  'ARCX',
                  style: GoogleFonts.inter(
                    color: textMuted,
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _isLoading ? '≈ ₹ ---' : '≈ ₹${NumberFormat('#,##0.00').format(double.tryParse(inrValue.toString()) ?? 0)}',
            style: GoogleFonts.inter(
              color: textMuted,
              fontSize: 14,
            ),
          ),
          if (!_isLoading) ...[
            const SizedBox(height: 12),
            // Flatcoin: Show stable "vault-backed" instead of volatile percentage
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.08),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    CupertinoIcons.shield,
                    color: accentGold.withValues(alpha: 0.7),
                    size: 12,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'Vault-backed currency',
                    style: GoogleFonts.inter(
                      color: textMuted,
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatRow(Map<String, dynamic>? wallet) {
    final totalDeposited = wallet?['total_deposited_inr'] ?? '0';
    final totalProfit = wallet?['total_profit_inr'] ?? '0';

    return Row(
      children: [
        Expanded(
          child: GlassContainer(
            borderRadius: 16,
            padding: const EdgeInsets.all(16),
            blur: 15,
            opacity: 0.06,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Total Deposited',
                  style: GoogleFonts.inter(
                    color: textMuted,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '₹${NumberFormat('#,##0').format(double.tryParse(totalDeposited.toString()) ?? 0)}',
                  style: GoogleFonts.inter(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: GlassContainer(
            borderRadius: 16,
            padding: const EdgeInsets.all(16),
            blur: 15,
            opacity: 0.06,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Total Profit',
                  style: GoogleFonts.inter(
                    color: textMuted,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '₹${NumberFormat('#,##0').format(double.tryParse(totalProfit.toString()) ?? 0)}',
                  style: GoogleFonts.inter(
                    color: arcxGreen,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildLinkedAccountsList(Map<String, dynamic>? wallet) {
    final user = wallet?['user'];
    final bankName = user?['bank_name']?.toString();
    final accountNumber = user?['bank_account_number']?.toString();

    if (bankName != null && bankName.isNotEmpty && accountNumber != null && accountNumber.isNotEmpty) {
      return [
        _buildBankTile(
          bankName: bankName,
          accountNumber: accountNumber,
        ),
      ];
    }

    return [
      Padding(
        padding: const EdgeInsets.all(20.0),
        child: Row(
          children: [
            Icon(CupertinoIcons.info_circle, color: textMuted.withValues(alpha: 0.5)),
            const SizedBox(width: 12),
            Text(
              'No Bank Account Linked',
              style: GoogleFonts.inter(color: textMuted, fontSize: 14),
            ),
          ],
        ),
      ),
    ];
  }

  Widget _buildBankTile({
    required String bankName,
    required String accountNumber,
  }) {
    // Mask account number
    final masked = accountNumber.length > 4 
        ? '•••• ${accountNumber.substring(accountNumber.length - 4)}'
        : accountNumber;

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          shape: BoxShape.circle,
        ),
        child: Center(
          child: Text(
            bankName.length >= 2 ? bankName.substring(0, 2).toUpperCase() : bankName.toUpperCase(),
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
          ),
        ),
      ),
      title: Text(
        bankName,
        style: GoogleFonts.inter(
          color: Colors.white,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      subtitle: Text(
        masked,
        style: GoogleFonts.inter(
          color: textMuted,
          fontSize: 12,
        ),
      ),
      trailing: const Icon(CupertinoIcons.chevron_right, color: Colors.white24, size: 16),
    );
  }

  Widget _buildCardTile() {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: accentGold.withValues(alpha: 0.1),
          shape: BoxShape.circle,
        ),
        child: const Icon(CupertinoIcons.creditcard_fill, color: accentGold, size: 20),
      ),
      title: Text(
        'ARCX Settlement Card',
        style: GoogleFonts.inter(
          color: Colors.white,
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      subtitle: Text(
        'Virtual • Active',
        style: GoogleFonts.inter(
          color: arcxGreen,
          fontSize: 12,
        ),
      ),
      trailing: const Icon(CupertinoIcons.chevron_right, color: Colors.white24, size: 16),
    );
  }

  Widget _buildLoadingSkeleton() {
    return GlassContainer(
      borderRadius: 20,
      padding: const EdgeInsets.all(20),
      child: const Center(
        child: CircularProgressIndicator(color: accentGold, strokeWidth: 2),
      ),
    );
  }
}
