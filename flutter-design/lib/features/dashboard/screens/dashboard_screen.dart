import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../payments/screens/deposit_screen.dart';
import '../../payments/screens/send_screen.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/providers/treasury_provider.dart';
import '../../../core/providers/wallet_provider.dart';
import '../../kyc/screens/kyc_screen.dart';
import 'wallet_screen.dart';
import 'analytics_screen.dart';
import 'profile_screen.dart';
import '../../payments/screens/withdraw_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  static const Color bgColor = Color(0xFF000000); 
  static const Color surfaceColor = Color(0xFF1C1C1E); 
  static const Color accentGold = Color(0xFFFFD60A);
  static const Color accentPurple = Color(0xFFA855F7); 
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  int _currentTab = 0;

  // Global state getters - these automatically watch the provider
  Map<String, dynamic>? get _walletData => ref.watch(walletProvider).data;
  bool get _isLoading => ref.watch(walletProvider).isLoading;

  static const _labels = ['Home', 'Wallet', 'Analytics', 'Profile'];
  static const _icons = [
    CupertinoIcons.house_fill,
    CupertinoIcons.money_dollar_circle_fill,
    CupertinoIcons.chart_bar_fill,
    CupertinoIcons.person_fill,
  ];

  @override
  void initState() {
    super.initState();
    // Load treasury data for chart
    Future.microtask(() {
      ref.read(treasuryProvider.notifier).loadTreasury();
      ref.read(treasuryProvider.notifier).loadHistory(period: '1W');
    });
  }

  void _loadWalletData() {
    ref.read(walletProvider.notifier).refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Stack(
          children: [
            // Tab Content
            Positioned.fill(
              child: IndexedStack(
                index: _currentTab,
                children: [
                  _buildHomeContent(context),
                  const WalletScreen(),
                  const AnalyticsScreen(),
                  const ProfileScreen(),
                ],
              ),
            ),
            
            // Floating Navigation Pill
            Positioned(
              bottom: 24,
              left: 24,
              right: 24,
              child: _buildFloatingNavBar(),
            ),
          ],
        ),
      ),
    );
  }

  void _handleFeatureTap(Widget destinationScreen) {
    final walletData = ref.read(walletProvider).data;
    if (walletData == null) return;
    
    final bool isVerified = walletData['user']?['is_kyc_verified'] ?? false;
    if (isVerified) {
      Navigator.push(context, MaterialPageRoute(builder: (context) => destinationScreen));
    } else {
      _showKycPrompt();
    }
  }

  void _showKycPrompt() {
    showModalBottomSheet(
      context: context,
      backgroundColor: surfaceColor,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (context) => Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(CupertinoIcons.shield, color: Colors.white, size: 48),
            const SizedBox(height: 16),
            Text(
              'Identity Verification Required',
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'To access financial features like Deposits and Sends, please complete your KYC verification.',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: textMuted, fontSize: 14),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.push(
                    context, 
                    MaterialPageRoute(builder: (context) => KycScreen(onVerificationComplete: _loadWalletData))
                  );
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                child: const Text('Verify Identity', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('Maybe Later', style: TextStyle(color: textMuted)),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  // Home tab content (the original dashboard)
  Widget _buildHomeContent(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.only(bottom: 100), // Space for nav pill
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 16),
            _buildAppBar(),
            const SizedBox(height: 24),
            _buildHeroCard(context),
            const SizedBox(height: 24),
            _buildActionRowContainer(),
            const SizedBox(height: 32),
            _buildTransactionsSection(),
          ],
        ),
      ),
    );
  }

  // 1. App Bar
  Widget _buildAppBar() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Greeting
        _buildGreeting(),

        // Right side: Notifications & Profile
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(CupertinoIcons.bell, color: Colors.white, size: 20),
        ),
      ],
    );
  }

  // 2. Greeting
  Widget _buildGreeting() {
    final user = _walletData?['user'];
    String firstName = user?['first_name']?.toString() ?? '';
    String lastName = user?['last_name']?.toString() ?? '';
    
    if (firstName.trim().isEmpty) {
      firstName = 'User';
    }
    final gender = user?['gender']?.toString() ?? '';

    String title = '';
    if (gender == 'F') {
      title = 'Mrs.';
    } else if (gender == 'M') {
      title = 'Mr.';
    }

    final greetingText = title.isNotEmpty && firstName != 'User' ? '$title $firstName' : firstName;
    final hour = DateTime.now().hour;
    String timeGreeting = 'Good Morning';
    if (hour >= 12 && hour < 17 ) {timeGreeting = 'Good Afternoon';}
    else if (hour >= 17) {timeGreeting = 'Good Evening';}

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          timeGreeting,
          style: GoogleFonts.inter(color: textMuted, fontSize: 13, fontWeight: FontWeight.w500),
        ),
        Text(
          greetingText,
          style: GoogleFonts.playfairDisplay(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }

  // 3. Hero Card - iOS Wallet Style
  Widget _buildHeroCard(BuildContext context) {
    final treasuryState = ref.watch(treasuryProvider);
    final history = treasuryState.historyData?['data'] as List? ?? [];
    final historyLoading = treasuryState.historyLoading || treasuryState.historyData == null;
    final arcxBalance = double.tryParse(_walletData?['arcx_balance'] ?? '0') ?? 0;
    final currentValueInr = double.tryParse(_walletData?['current_value_inr'] ?? '0') ?? 0;

    // Parse price — try USD first, then INR
    final arcxPriceUsd = treasuryState.data?['arcx_price_usd'];
    final arcxPriceInr = treasuryState.data?['arcx_price_inr'];
    String priceDisplay = '---';
    if (arcxPriceInr != null) {
      final val = double.tryParse(arcxPriceInr.toString()) ?? 0;
      priceDisplay = '₹${val.toStringAsFixed(2)}';
    } else if (arcxPriceUsd != null) {
      final val = double.tryParse(arcxPriceUsd.toString()) ?? 0;
      priceDisplay = '\$${val.toStringAsFixed(4)}';
    }

    return Container(
      width: double.infinity,
      height: 200,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF2C2C2E), Color(0xFF1C1C1E)],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
        boxShadow: [
          BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 20, offset: const Offset(0, 10)),
        ],
      ),
      child: Stack(
        children: [
          Positioned(
            right: -30, bottom: -30,
            child: Container(
              width: 150, height: 150,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [accentGold.withValues(alpha: 0.1), Colors.transparent],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 32, height: 32,
                              decoration: BoxDecoration(
                                color: accentGold.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Center(child: Text('A', style: TextStyle(color: accentGold, fontWeight: FontWeight.bold, fontSize: 18))),
                            ),
                            const SizedBox(width: 8),
                            Text('ARCX', style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.7), fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 2)),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          _isLoading ? '---' : NumberFormat('#,##0.00').format(arcxBalance),
                          style: GoogleFonts.inter(color: Colors.white, fontSize: 36, fontWeight: FontWeight.w700, letterSpacing: -1),
                        ),
                      ],
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text('Price', style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.5), fontSize: 10)),
                          Text(priceDisplay, style: GoogleFonts.inter(color: accentGold, fontSize: 14, fontWeight: FontWeight.w700)),
                        ],
                      ),
                    ),
                  ],
                ),
                const Spacer(),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '₹${_isLoading ? '---' : NumberFormat('#,##0.00').format(currentValueInr)}',
                          style: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.6), fontSize: 16, fontWeight: FontWeight.w500),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Container(width: 8, height: 8, decoration: const BoxDecoration(color: arcxGreen, shape: BoxShape.circle)),
                            const SizedBox(width: 6),
                            Text('Stable Value', style: GoogleFonts.inter(color: arcxGreen, fontSize: 11, fontWeight: FontWeight.w500)),
                          ],
                        ),
                      ],
                    ),
                    if (!historyLoading && history.length > 2)
                      SizedBox(width: 100, height: 50, child: _buildMiniChart(history))
                    else
                      SizedBox(
                        width: 100, height: 50,
                        child: Center(
                          child: historyLoading
                              ? const CupertinoActivityIndicator(radius: 8)
                              : Text('No data', style: GoogleFonts.inter(color: textMuted, fontSize: 10)),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMiniChart(List history) {
    final spots = <FlSpot>[];
    for (int i = 0; i < history.length; i++) {
      final price = double.tryParse(history[i]['price_usd']?.toString() ?? '0') ?? 0;
      if (price > 0) {
        spots.add(FlSpot(i.toDouble(), price));
      }
    }

    if (spots.length < 2) return const SizedBox();

    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: const Color(0xFFE0E0E0),
            barWidth: 2,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: const Color(0xFFE0E0E0).withValues(alpha: 0.1),
            ),
          ),
        ],
        lineTouchData: const LineTouchData(enabled: false),
      ),
    );
  }

  Widget _buildActionRowContainer() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _buildActionItem(CupertinoIcons.add, 'Deposit', () => _handleFeatureTap(const DepositScreen())),
        _buildActionItem(CupertinoIcons.arrow_up_right, 'Send', () => _handleFeatureTap(const SendScreen())),
        _buildActionItem(CupertinoIcons.arrow_down_left, 'Withdraw', () => _handleFeatureTap(const WithdrawScreen())),
        _buildActionItem(CupertinoIcons.qrcode_viewfinder, 'Scan & Pay', () {}),
      ],
    );
  }

  Widget _buildActionItem(IconData icon, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 56, height: 56,
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.05), shape: BoxShape.circle),
            child: Icon(icon, color: Colors.white, size: 24),
          ),
          const SizedBox(height: 8),
          Text(label, style: GoogleFonts.inter(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  Widget _buildTransactionsSection() {
    final transactions = _walletData?['recent_transactions'] ?? [];
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Recent Activity', style: GoogleFonts.playfairDisplay(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600)),
            Text('See All', style: GoogleFonts.inter(color: accentGold, fontSize: 12, fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 16),
        if (transactions.isEmpty) _buildEmptyState()
        else _buildGlassSection(transactions.take(5).map<Widget>((tx) => _buildTransactionTileFromData(tx)).toList()),
      ],
    );
  }

  Widget _buildEmptyState() {
    return GlassContainer(
      borderRadius: 20, padding: const EdgeInsets.all(32),
      child: Center(
        child: Column(
          children: [
            Icon(CupertinoIcons.tray, color: textMuted.withValues(alpha: 0.3), size: 48),
            const SizedBox(height: 16),
            Text('No transactions yet', style: GoogleFonts.inter(color: textMuted, fontSize: 14)),
          ],
        ),
      ),
    );
  }

  Widget _buildGlassSection(List<Widget> children) {
    return GlassContainer(
      borderRadius: 20, padding: const EdgeInsets.all(8),
      child: Column(children: children),
    );
  }

  Widget _buildTransactionTileFromData(dynamic tx) {
    return ListTile(
      leading: CircleAvatar(backgroundColor: Colors.white.withValues(alpha: 0.05), child: Icon(CupertinoIcons.money_dollar, color: Colors.white, size: 18)),
      title: Text(tx['note'] ?? 'Transaction', style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w500)),
      subtitle: Text(tx['status'] ?? 'Completed', style: GoogleFonts.inter(color: textMuted, fontSize: 12)),
      trailing: Text('₹${tx['inr_amount']}', style: GoogleFonts.inter(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
    );
  }

  Widget _buildFloatingNavBar() {
    return GlassContainer(
      borderRadius: 30, padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      blur: 20, opacity: 0.1,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: List<Widget>.generate(_labels.length, (index) => _buildNavItem(index)),
      ),
    );
  }

  Widget _buildNavItem(int index) {
    final isSelected = _currentTab == index;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => setState(() => _currentTab = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOutCubic,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(color: isSelected ? Colors.white.withValues(alpha: 0.1) : Colors.transparent, borderRadius: BorderRadius.circular(20)),
        child: Row(
          children: [
            Icon(_icons[index], color: isSelected ? Colors.white : textMuted, size: 20),
            if (isSelected) ...[
              const SizedBox(width: 8),
              Text(_labels[index], style: GoogleFonts.inter(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
            ],
          ],
        ),
      ),
    );
  }
}
