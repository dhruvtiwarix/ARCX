import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../network/api_service.dart';

class WalletState {
  final Map<String, dynamic>? data;
  final bool isLoading;
  final String? error;

  WalletState({this.data, this.isLoading = false, this.error});

  WalletState copyWith({Map<String, dynamic>? data, bool? isLoading, String? error}) {
    return WalletState(
      data: data ?? this.data,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class WalletNotifier extends Notifier<WalletState> {
  final _api = ApiService();

  @override
  WalletState build() {
    // Start loading on initialization
    Future.microtask(() => loadWallet());
    return WalletState(isLoading: true);
  }

  Future<void> loadWallet() async {
    state = state.copyWith(isLoading: true);

    // Fetch wallet and user profile in parallel
    final results = await Future.wait([
      _api.getWallet(),
      _api.getUserProfile(),
    ]);

    final walletData = results[0];
    final userProfile = results[1];

    if (kDebugMode) {
      print('[ARCX] getWallet result: $walletData');
      print('[ARCX] getUserProfile result: $userProfile');
      print('[ARCX] getUserProfile type: ${userProfile.runtimeType}');
    }

    if (walletData != null || userProfile != null) {
      final combinedData = Map<String, dynamic>.from(walletData ?? {});

      if (userProfile != null) {
        if (kDebugMode) print('[ARCX] userProfile keys: ${userProfile.keys.toList()}');

        // API returns { 'user': {...} }, extract the inner data
        if (userProfile['user'] != null) {
          combinedData['user'] = userProfile['user'];
          if (kDebugMode) print('[ARCX] Extracted user from userProfile[user]');
        } else {
          // Fallback: use directly if not wrapped
          combinedData['user'] = userProfile;
          if (kDebugMode) print('[ARCX] Using userProfile directly');
        }
      }
      if (kDebugMode) print('[ARCX] Wallet data keys: ${combinedData.keys.toList()}');
      state = WalletState(data: combinedData, isLoading: false);
    } else {
      state = state.copyWith(isLoading: false, error: 'Failed to fetch wallet data');
    }
  }

  Future<void> refresh() async {
    await loadWallet();
  }

  void updateData(Map<String, dynamic> newData) {
    state = WalletState(data: newData, isLoading: false);
  }
}

final walletProvider = NotifierProvider<WalletNotifier, WalletState>(() {
  return WalletNotifier();
});
