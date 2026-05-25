import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../network/api_service.dart';

class TreasuryState {
  final Map<String, dynamic>? data;
  final Map<String, dynamic>? historyData;
  final bool isLoading;
  final bool historyLoading;
  final String? error;

  TreasuryState({this.data, this.historyData, this.isLoading = true, this.historyLoading = true, this.error});

  TreasuryState copyWith({
    Map<String, dynamic>? data,
    Map<String, dynamic>? historyData,
    bool? isLoading,
    bool? historyLoading,
    String? error,
    int? version,
  }) {
    return TreasuryState(
      data: data ?? this.data,
      historyData: historyData ?? this.historyData,
      isLoading: isLoading ?? this.isLoading,
      historyLoading: historyLoading ?? this.historyLoading,
      error: error ?? this.error,
    );
  }
}

class TreasuryNotifier extends Notifier<TreasuryState> {
  Timer? _pollingTimer;
  int _version = 0;

  int get version => _version;

  @override
  TreasuryState build() {
    Future.microtask(() => loadTreasury());
    _pollingTimer = Timer.periodic(const Duration(hours: 24), (_) => loadTreasury());
    ref.onDispose(() => _pollingTimer?.cancel());
    return TreasuryState();
  }

  void _bump() { _version++; }

  Future<void> loadTreasury() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final api = ApiService();
      final treasuryData = await api.getTreasury();
      if (treasuryData != null) {
        _bump();
        state = state.copyWith(data: treasuryData, isLoading: false);
      } else {
        state = state.copyWith(isLoading: false, error: 'Failed to load treasury data');
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadHistory({String period = '1M'}) async {
    state = state.copyWith(historyLoading: true);
    try {
      final baseUrl = ApiService.baseUrl;
      final response = await http.get(
        Uri.parse('$baseUrl/treasury/history/?period=$period'),
      ).timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        final List<dynamic> history = jsonDecode(response.body);
        _bump();
        state = state.copyWith(historyData: {'period': period, 'data': history}, historyLoading: false);
      } else {
        state = state.copyWith(historyLoading: false);
      }
    } catch (e) {
      state = state.copyWith(historyLoading: false);
    }
  }
}

final treasuryProvider = NotifierProvider<TreasuryNotifier, TreasuryState>(() {
  return TreasuryNotifier();
});
