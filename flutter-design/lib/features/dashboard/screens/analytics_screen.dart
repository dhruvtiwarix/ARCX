import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/widgets/glass_container.dart';
import '../../../core/network/api_service.dart';
import '../../../core/providers/treasury_provider.dart';
import '../../../core/providers/wallet_provider.dart';

class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  // static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color textMuted = Color(0xFF8E8E93);
  // static const Color arcxGreen = Color(0xFF30D158);
  static const Color accentGold = Color(0xFFFFD60A);

  String _selectedPeriod = '1M';
  final ApiService _apiService = ApiService();

  final List<String> _periods = ['1W', '1M', '3M', '1Y', 'ALL'];

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(treasuryProvider.notifier).loadHistory());
  }

  Future<void> _refreshData() async {
    await ref.read(walletProvider.notifier).refresh();
    await ref.read(treasuryProvider.notifier).loadHistory(period: _selectedPeriod);
  }

  @override
  Widget build(BuildContext context) {
    final treasuryState = ref.watch(treasuryProvider);
    final historyData = treasuryState.historyData;
    final historyLoading = treasuryState.historyLoading;
    final walletState = ref.watch(walletProvider);
    final walletData = walletState.data;
    final isLoading = walletState.isLoading;

    final hasHistory = historyData?['data'] != null && (historyData!['data'] as List).isNotEmpty;

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
              'Analytics',
              style: GoogleFonts.playfairDisplay(
                color: Colors.white,
                fontSize: 28,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Portfolio performance over time',
              style: GoogleFonts.inter(color: textMuted, fontSize: 14),
            ),
            const SizedBox(height: 32),

            // Time Period Toggles
            _buildPeriodSelector(),
            const SizedBox(height: 32),

            // Large Chart
            SizedBox(
              height: 200,
              child: historyLoading
                  ? const Center(child: CupertinoActivityIndicator())
                  : hasHistory
                      ? _buildDynamicChart(historyData['data'] as List)
                      : _buildPlaceholderChart(),
            ),
            const SizedBox(height: 32),

            // Asset Allocation Section
            // _buildAssetAllocationSection(treasuryState.data),
            // const SizedBox(height: 32),

            // Stats Row
            _buildStatsGrid(walletData, isLoading),
            const SizedBox(height: 100),
          ],
        ),
      ),
    );
  }

  Widget _buildPeriodSelector() {
    return SizedBox(
      width: double.infinity,
      child: CupertinoSlidingSegmentedControl<String>(
        backgroundColor: surfaceColor,
        thumbColor: Colors.white.withValues(alpha: 0.15),
        groupValue: _selectedPeriod,
        onValueChanged: (String? value) {
          if (value != null) {
            setState(() => _selectedPeriod = value);
            ref.read(treasuryProvider.notifier).loadHistory(period: value);
          }
        },
        children: {
          for (final period in _periods)
            period: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Text(
                period,
                style: GoogleFonts.inter(
                  color: _selectedPeriod == period ? Colors.white : textMuted,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
        },
      ),
    );
  }

  Widget _buildDynamicChart(List<dynamic> history) {
    if (history.isEmpty) {
      return _buildPlaceholderChart();
    }

    // Convert history to chart spots
    final spots = <FlSpot>[];
    double minY = double.infinity;
    double maxY = 0;

    for (int i = 0; i < history.length; i++) {
      final price = double.tryParse(history[i]['price_usd']?.toString() ?? '0') ?? 0;
      if (price > 0) {
        spots.add(FlSpot(i.toDouble(), price));
        if (price < minY) minY = price;
        if (price > maxY) maxY = price;
      }
    }

    if (spots.isEmpty) {
      return _buildPlaceholderChart();
    }

    // Add padding to min/max
    minY = minY * 0.98;
    maxY = maxY * 1.02;

    // Flatcoin: Always use calm silver/white - no red/green volatility indicators
    const Color chartColor = Color(0xFFE0E0E0);

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: (maxY - minY) / 4,
          getDrawingHorizontalLine: (value) => FlLine(
            color: Colors.white.withValues(alpha: 0.05),
            strokeWidth: 1,
          ),
        ),
        titlesData: FlTitlesData(
          leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: (spots.length / 4).ceilToDouble(),
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx >= 0 && idx < history.length) {
                  final timestamp = history[idx]['timestamp'];
                  if (timestamp != null) {
                    final date = DateTime.tryParse(timestamp.toString());
                    if (date != null) {
                      return Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          DateFormat('dd/MM').format(date),
                          style: GoogleFonts.inter(
                            color: const Color(0xFF8E8E93),
                            fontSize: 10,
                          ),
                        ),
                      );
                    }
                  }
                }
                return const SizedBox.shrink();
              },
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: (spots.length - 1).toDouble(),
        minY: minY,
        maxY: maxY,
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: chartColor,
            barWidth: 2,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                colors: [
                  chartColor.withValues(alpha: 0.15),
                  chartColor.withValues(alpha: 0.0),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlaceholderChart() {
    return LineChart(
      LineChartData(
        gridData: const FlGridData(show: false),
        titlesData: const FlTitlesData(show: false),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: 10,
        minY: 0,
        maxY: 10,
        lineBarsData: [
          LineChartBarData(
            spots: List.generate(11, (i) => FlSpot(i.toDouble(), 3 + (i % 3) * 1.5)),
            isCurved: true,
            color: Colors.white.withValues(alpha: 0.1),
            barWidth: 1.5,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                colors: [
                  Colors.white.withValues(alpha: 0.05),
                  Colors.white.withValues(alpha: 0.0),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsGrid(Map<String, dynamic>? walletData, bool isLoading) {
    if (isLoading) {
      return _buildGlassSection([
        _buildLoadingStatTile(),
        _buildLoadingStatTile(),
        _buildLoadingStatTile(),
        _buildLoadingStatTile(),
      ]);
    }

    final totalDeposited = double.tryParse(walletData?['total_deposited_inr']?.toString() ?? '0') ?? 0;
    final currentValue = double.tryParse(walletData?['current_value_inr']?.toString() ?? '0') ?? 0;
    final profit = double.tryParse(walletData?['total_profit_inr']?.toString() ?? '0') ?? 0;
    final profitPct = double.tryParse(walletData?['profit_pct']?.toString() ?? '0') ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'PORTFOLIO SUMMARY',
            style: GoogleFonts.inter(
              color: textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.5,
            ),
          ),
        ),
        _buildGlassSection([
          _buildStatListTile(
            icon: CupertinoIcons.arrow_down_to_line,
            label: 'Total Invested',
            value: '₹${NumberFormat('#,##0').format(totalDeposited)}',
          ),
          _buildStatListTile(
            icon: CupertinoIcons.briefcase,
            label: 'Current Value',
            value: '₹${NumberFormat('#,##0').format(currentValue)}',
          ),
          _buildStatListTile(
            icon: CupertinoIcons.chart_bar_alt_fill,
            label: 'Total Growth',
            value: '₹${NumberFormat('#,##0').format(profit.abs())}',
            valueColor: Colors.white,
          ),
          _buildStatListTile(
            icon: CupertinoIcons.percent,
            label: 'APY',
            value: '${profitPct.toStringAsFixed(1)}%',
            valueColor: accentGold,
          ),
        ]),
      ],
    );
  }

  Widget _buildStatListTile({
    required IconData icon,
    required String label,
    required String value,
    Color? valueColor,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              icon,
              color: Colors.white.withValues(alpha: 0.85),
              size: 16,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: Colors.white,
                fontSize: 13.5,
                fontWeight: FontWeight.w400,
              ),
            ),
          ),
          Text(
            value,
            style: GoogleFonts.inter(
              color: valueColor ?? Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingStatTile() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          const SizedBox(width: 12),
          Container(
            width: 100,
            height: 14,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const Spacer(),
          Container(
            width: 60,
            height: 14,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildLegendItem(Color color, String label, String value) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 10),
        Text(
          label,
          style: GoogleFonts.inter(
            color: Colors.white,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
        const Spacer(),
        Text(
          value,
          style: GoogleFonts.inter(
            color: textMuted,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildGlassSection(List<Widget> children) {
    return GlassContainer(
      borderRadius: 16,
      blur: 25,
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
}