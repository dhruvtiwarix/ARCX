import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../network/api_service.dart';

class SettlementState {
  final double navPriceUsd;
  final double navPriceInr;
  final double fxRate;
  final bool isMarketOpen;
  final bool isLoadingPrices;
  
  final String? activeQuoteId;
  final double lockedBidInr;
  final double lockedAskInr;
  final int secondsRemaining;
  final bool isQuoteValid;

  SettlementState({
    this.navPriceUsd = 0.0,
    this.navPriceInr = 0.0,
    this.fxRate = 83.50,
    this.isMarketOpen = true,
    this.isLoadingPrices = false,
    this.activeQuoteId,
    this.lockedBidInr = 0.0,
    this.lockedAskInr = 0.0,
    this.secondsRemaining = 0,
    this.isQuoteValid = false,
  });

  SettlementState copyWith({
    double? navPriceUsd,
    double? navPriceInr,
    double? fxRate,
    bool? isMarketOpen,
    bool? isLoadingPrices,
    String? activeQuoteId,
    double? lockedBidInr,
    double? lockedAskInr,
    int? secondsRemaining,
    bool? isQuoteValid,
  }) {
    return SettlementState(
      navPriceUsd: navPriceUsd ?? this.navPriceUsd,
      navPriceInr: navPriceInr ?? this.navPriceInr,
      fxRate: fxRate ?? this.fxRate,
      isMarketOpen: isMarketOpen ?? this.isMarketOpen,
      isLoadingPrices: isLoadingPrices ?? this.isLoadingPrices,
      activeQuoteId: activeQuoteId ?? this.activeQuoteId,
      lockedBidInr: lockedBidInr ?? this.lockedBidInr,
      lockedAskInr: lockedAskInr ?? this.lockedAskInr,
      secondsRemaining: secondsRemaining ?? this.secondsRemaining,
      isQuoteValid: isQuoteValid ?? this.isQuoteValid,
    );
  }
}

class SettlementNotifier extends Notifier<SettlementState> {
  final ApiService _api = ApiService();
  Timer? _priceTimer;
  Timer? _quoteTimer;
  DateTime? _quoteExpiry;

  @override
  SettlementState build() {
    // Start price sync on init
    _startPriceSync();
    
    ref.onDispose(() {
      _priceTimer?.cancel();
      _quoteTimer?.cancel();
    });

    return SettlementState();
  }

  void _startPriceSync() {
    _priceTimer?.cancel();
    fetchPrices();
    _priceTimer = Timer.periodic(const Duration(seconds: 30), (_) => fetchPrices());
  }

  Future<void> fetchPrices() async {
    state = state.copyWith(isLoadingPrices: true);
    final data = await _api.getLivePrices();
    
    if (data != null) {
      state = state.copyWith(
        navPriceUsd: double.tryParse(data['nav_price_usd'].toString()) ?? 0.0,
        navPriceInr: double.tryParse(data['nav_price_inr'].toString()) ?? 0.0,
        fxRate: double.tryParse(data['fx_rate_usd_inr'].toString()) ?? 83.50,
        isMarketOpen: data['is_market_open'] ?? true,
        isLoadingPrices: false,
      );
    } else {
      state = state.copyWith(isLoadingPrices: false);
    }
  }

  Future<bool> requestQuote(String action) async {
    _quoteTimer?.cancel();
    state = state.copyWith(activeQuoteId: null, isQuoteValid: false);

    final data = await _api.getQuote(action);
    if (data != null) {
      _quoteExpiry = DateTime.parse(data['expires_at']);
      state = state.copyWith(
        activeQuoteId: data['quote_id'],
        lockedBidInr: double.tryParse(data['bid_price_inr'].toString()) ?? 0.0,
        lockedAskInr: double.tryParse(data['ask_price_inr'].toString()) ?? 0.0,
        isQuoteValid: true,
      );
      _startQuoteCountdown();
      return true;
    }
    return false;
  }

  void _startQuoteCountdown() {
    _quoteTimer?.cancel();
    _updateRemainingSeconds();
    
    _quoteTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      _updateRemainingSeconds();
      if (state.secondsRemaining <= 0) {
        state = state.copyWith(activeQuoteId: null, isQuoteValid: false);
        timer.cancel();
      }
    });
  }

  void _updateRemainingSeconds() {
    if (_quoteExpiry == null) return;
    final seconds = _quoteExpiry!.difference(DateTime.now()).inSeconds;
    state = state.copyWith(secondsRemaining: seconds);
  }

  void cancelQuote() {
    _quoteTimer?.cancel();
    state = state.copyWith(activeQuoteId: null, isQuoteValid: false, secondsRemaining: 0);
  }

  Future<Map<String, dynamic>?> executeWithdraw(double amountArcx) async {
    if (!state.isQuoteValid || state.activeQuoteId == null) return null;
    final result = await _api.withdraw(amountArcx, state.activeQuoteId!);
    if (result != null) cancelQuote();
    return result;
  }

  Future<Map<String, dynamic>?> executeSend(String email, double amountArcx) async {
    if (!state.isQuoteValid || state.activeQuoteId == null) return null;
    final result = await _api.sendArcx(email, amountArcx, state.activeQuoteId!);
    if (result != null) cancelQuote();
    return result;
  }
}

final settlementProvider = NotifierProvider<SettlementNotifier, SettlementState>(() {
  return SettlementNotifier();
});
