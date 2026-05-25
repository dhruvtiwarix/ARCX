import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/security_service.dart';

class SecurityState {
  final bool isBiometricAvailable;
  final bool isBiometricEnrolled;
  final bool isDeviceVerified;
  final bool requiresAuth;

  SecurityState({
    this.isBiometricAvailable = false,
    this.isBiometricEnrolled = false,
    this.isDeviceVerified = false,
    this.requiresAuth = false,
  });
}

class SecurityNotifier extends Notifier<SecurityState> {
  @override
  SecurityState build() {
    return SecurityState();
  }

  Future<void> checkSecurityStatus() async {
    final status = await SecurityService.getSecurityStatus();
    state = SecurityState(
      isBiometricAvailable: status['biometric_available'] ?? false,
      isBiometricEnrolled: status['biometric_enrolled'] ?? false,
      isDeviceVerified: status['device_verified'] ?? false,
      requiresAuth: status['biometric_enrolled'] ?? false,
    );
  }

  Future<bool> authenticate() async {
    if (!state.isBiometricEnrolled) return true;
    return await SecurityService.authenticate();
  }
}

final securityProvider = NotifierProvider<SecurityNotifier, SecurityState>(() {
  return SecurityNotifier();
});