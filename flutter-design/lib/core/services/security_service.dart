import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';

class SecurityService {
  static final LocalAuthentication _auth = LocalAuthentication();
  static final FlutterSecureStorage _secureStorage = const FlutterSecureStorage();

  // Storage keys
  static const String _deviceIdKey = 'arcx_device_id';
  static const String _biometricEnrolledKey = 'arcx_biometric_enrolled';
  static const String _deviceBindingKey = 'arcx_device_binding';

  /// Check if device supports biometrics
  static Future<bool> isBiometricAvailable() async {
    try {
      final canAuthenticateWithBiometrics = await _auth.canCheckBiometrics;
      final canAuthenticate = canAuthenticateWithBiometrics || await _auth.isDeviceSupported();
      return canAuthenticate;
    } catch (e) {
      return false;
    }
  }

  /// Get available biometric types
  static Future<List<BiometricType>> getAvailableBiometrics() async {
    try {
      return await _auth.getAvailableBiometrics();
    } catch (e) {
      return [];
    }
  }

  /// Enroll biometrics - generate device binding on first login
  static Future<bool> enrollBiometrics() async {
    try {
      // Generate unique device identifier
      final deviceId = await _generateDeviceId();

      // Store device binding
      await _secureStorage.write(key: _deviceIdKey, value: deviceId);
      await _secureStorage.write(key: _biometricEnrolledKey, value: 'true');

      return true;
    } catch (e) {
      return false;
    }
  }

  /// Disable biometrics
  static Future<bool> disableBiometrics() async {
    try {
      await _secureStorage.delete(key: _biometricEnrolledKey);
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Authenticate with biometrics
  static Future<bool> authenticate({String reason = 'Authenticate to access ARCX'}) async {
    try {
      final authenticated = await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false,
        ),
      );
      return authenticated;
    } catch (e) {
      return false;
    }
  }

  /// Check if biometrics are enrolled
  static Future<bool> isBiometricEnrolled() async {
    final enrolled = await _secureStorage.read(key: _biometricEnrolledKey);
    return enrolled == 'true';
  }

  /// Verify device binding - check if this is the same device
  static Future<bool> verifyDeviceBinding() async {
    final storedDeviceId = await _secureStorage.read(key: _deviceIdKey);
    if (storedDeviceId == null) return false;

    final currentDeviceId = await _generateDeviceId();
    return storedDeviceId == currentDeviceId;
  }

  /// Generate unique device ID based on device characteristics
  static Future<String> _generateDeviceId() async {
    // In production, use device_info_plus to get actual device IDs
    // For now, generate a stable device fingerprint
    final stored = await _secureStorage.read(key: _deviceBindingKey);
    if (stored != null) return stored;

    // Generate new device fingerprint
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final random = timestamp.hashCode.abs().toString();
    final deviceFingerprint = 'arcx_device_$random';

    await _secureStorage.write(key: _deviceBindingKey, value: deviceFingerprint);
    return deviceFingerprint;
  }

  /// Clear all security data (logout)
  static Future<void> clearSecurityData() async {
    await _secureStorage.delete(key: _deviceIdKey);
    await _secureStorage.delete(key: _biometricEnrolledKey);
    await _secureStorage.delete(key: _deviceBindingKey);
    await _secureStorage.delete(key: 'auth_token');
  }

  /// Get device binding status
  static Future<Map<String, dynamic>> getSecurityStatus() async {
    final isEnrolled = await isBiometricEnrolled();
    final isDeviceVerified = await verifyDeviceBinding();
    final hasBiometrics = await isBiometricAvailable();
    final biometrics = await getAvailableBiometrics();

    return {
      'biometric_enrolled': isEnrolled,
      'device_verified': isDeviceVerified,
      'biometric_available': hasBiometrics,
      'biometric_type': _getBiometricLabel(biometrics),
    };
  }

  static String _getBiometricLabel(List<BiometricType> types) {
    if (types.contains(BiometricType.face)) return 'Face ID';
    if (types.contains(BiometricType.fingerprint)) return 'Fingerprint';
    if (types.contains(BiometricType.iris)) return 'Iris';
    return 'Biometrics';
  }
}