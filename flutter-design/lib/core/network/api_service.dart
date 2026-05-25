import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:crypto/crypto.dart';

class ApiService {
  /// Backend URL configuration:
  ///  - Windows desktop app: 127.0.0.1
  ///  - Android emulator:    10.0.2.2
  ///  - Physical phone:      Your PC's WiFi IP (192.168.1.7)
  ///  - Web browser:         127.0.0.1
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api';
    try {
      if (Platform.isAndroid) {
        // Use your PC's WiFi IP for physical phones.
        // Change this to 'http://10.0.2.2:8000/api' if using Android emulator.
        return 'http://192.168.1.7:8000/api';
      }
      if (Platform.isWindows) return 'http://127.0.0.1:8000/api';
    } catch (_) {}
    return 'http://127.0.0.1:8000/api';
  }

  static const _androidOptions = AndroidOptions(encryptedSharedPreferences: true);
  static const _iosOptions = IOSOptions(accessibility: KeychainAccessibility.first_unlock);

  final storage = const FlutterSecureStorage(
    aOptions: _androidOptions,
    iOptions: _iosOptions,
  );


  // ───────────────────────── Auth ─────────────────────────

  /// Request an OTP for the given email. Returns true on success.
  Future<bool> sendOtp(String email) async {
    try {
      if (kDebugMode) print('[ARCX] Sending OTP to $email via $baseUrl');
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/send-otp/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email}),
          )
          .timeout(const Duration(seconds: 30));

      if (kDebugMode) {
        print('[ARCX] sendOtp response: ${response.statusCode} ${response.body}');
      }
      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] sendOtp error: $e');
      return false;
    }
  }

  /// Verify the OTP. On success, saves the auth token and returns true.
  Future<bool> verifyOtp(String email, String otp) async {
    try {
      if (kDebugMode) print('[ARCX] Verifying OTP for $email');
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/verify-otp/'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email, 'otp': otp}),
          )
          .timeout(const Duration(seconds: 15));

      if (kDebugMode) {
        print('[ARCX] verifyOtp response: ${response.statusCode} ${response.body}');
      }

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['token'];
        await storage.write(key: 'auth_token', value: token);
        return true;
      }
      return false;
    } catch (e) {
      if (kDebugMode) print('[ARCX] verifyOtp error: $e');
      return false;
    }
  }

  /// Submit KYC details. Returns true on success.
  Future<bool> submitKyc(String phoneNumber, String panNumber) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/kyc/'),
            headers: headers,
            body: jsonEncode({'phone_number': phoneNumber, 'pan_number': panNumber}),
          )
          .timeout(const Duration(seconds: 15));

      if (kDebugMode) {
        print('[ARCX] submitKyc response: ${response.statusCode} ${response.body}');
      }
      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] submitKyc error: $e');
      return false;
    }
  }

  // Multi-step KYC APIs
  Future<bool> submitKycStep1({
    required String firstName,
    required String lastName,
    required DateTime dateOfBirth,
    required String gender,
    required String phoneNumber,
  }) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/kyc/step1/'),
            headers: headers,
            body: jsonEncode({
              'first_name': firstName,
              'last_name': lastName,
              'date_of_birth': dateOfBirth.toIso8601String().split('T')[0],
              'gender': gender,
              'phone_number': phoneNumber,
            }),
          )
          .timeout(const Duration(seconds: 15));

      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] submitKycStep1 error: $e');
      return false;
    }
  }

  Future<bool> submitKycStep2({
    required String addressLine1,
    String? addressLine2,
    required String city,
    required String state,
    required String pincode,
  }) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/kyc/step2/'),
            headers: headers,
            body: jsonEncode({
              'address_line1': addressLine1,
              'address_line2': addressLine2 ?? '',
              'city': city,
              'state': state,
              'pincode': pincode,
            }),
          )
          .timeout(const Duration(seconds: 15));

      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] submitKycStep2 error: $e');
      return false;
    }
  }

  Future<bool> submitKycStep3({
    required String panNumber,
    required String aadhaarNumber,
  }) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/kyc/step3/'),
            headers: headers,
            body: jsonEncode({
              'pan_number': panNumber,
              'aadhaar_number': aadhaarNumber,
            }),
          )
          .timeout(const Duration(seconds: 15));

      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] submitKycStep3 error: $e');
      return false;
    }
  }

  Future<bool> submitKycStep4({
    required String bankName,
    required String bankAccountNumber,
    required String bankIfsc,
    required String bankAccountHolder,
  }) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/kyc/step4/'),
            headers: headers,
            body: jsonEncode({
              'bank_name': bankName,
              'bank_account_number': bankAccountNumber,
              'bank_ifsc': bankIfsc,
              'bank_account_holder': bankAccountHolder,
            }),
          )
          .timeout(const Duration(seconds: 15));

      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] submitKycStep4 error: $e');
      return false;
    }
  }

  Future<bool> completeKyc() async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/kyc/complete/'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 15));

      if (kDebugMode) print('[ARCX] completeKyc: ${response.statusCode} ${response.body}');
      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] completeKyc error: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getKycStatus() async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .get(
            Uri.parse('$baseUrl/auth/kyc/status/'),
            headers: headers,
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] getKycStatus error: $e');
      return null;
    }
  }

  /// Get User Profile
  Future<Map<String, dynamic>?> getUserProfile() async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .get(Uri.parse('$baseUrl/auth/profile/'), headers: headers)
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        if (kDebugMode) print('[ARCX] getUserProfile response: ${response.body}');
        return jsonDecode(response.body);
      }
      if (kDebugMode) print('[ARCX] getUserProfile status: ${response.statusCode}');
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] getUserProfile error: $e');
      return null;
    }
  }

  /// Update Profile (PATCH)
  Future<Map<String, dynamic>?> updateProfile(Map<String, String> fields) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .patch(
            Uri.parse('$baseUrl/auth/profile/'),
            headers: headers,
            body: jsonEncode(fields),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] updateProfile error: $e');
      return null;
    }
  }

  /// Upload Profile Photo
  Future<Map<String, dynamic>?> uploadProfilePhoto(String filePath) async {
    try {
      final token = await getToken();
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/auth/profile/photo/'),
      );
      request.headers['Authorization'] = 'Token $token';
      request.files.add(await http.MultipartFile.fromPath('photo', filePath));

      final streamedResponse = await request.send().timeout(const Duration(seconds: 30));
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] uploadProfilePhoto error: $e');
      return null;
    }
  }

  // ───────────────────── ARCX PIN ──────────────────────

  /// Set ARCX Transaction PIN
  Future<bool> setPin(String pin) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/pin/set/'),
            headers: headers,
            body: jsonEncode({'pin': pin}),
          )
          .timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('[ARCX] setPin error: $e');
      return false;
    }
  }

  /// Verify ARCX Transaction PIN
  Future<bool> verifyPin(String pin) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/pin/verify/'),
            headers: headers,
            body: jsonEncode({'pin': pin}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['valid'] == true;
      }
      return false;
    } catch (e) {
      if (kDebugMode) print('[ARCX] verifyPin error: $e');
      return false;
    }
  }

  // ───────────────────── Session ──────────────────────

  /// Check if the user has an active session.
  Future<bool> isLoggedIn() async {
    final token = await storage.read(key: 'auth_token');
    return token != null;
  }

  /// Get the stored auth token for API calls.
  Future<String?> getToken() async {
    return await storage.read(key: 'auth_token');
  }

  /// Clear the stored token (logout).
  Future<void> logout() async {
    await storage.delete(key: 'auth_token');
  }

  /// Helper: get auth headers with token.
  Future<Map<String, String>> _authHeaders() async {
    final token = await getToken();
    return {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    };
  }

  // ───────────────────── Wallet ──────────────────────

  /// Get the user's wallet data (balance, profit, transactions).
  Future<Map<String, dynamic>?> getWallet() async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .get(Uri.parse('$baseUrl/wallet/'), headers: headers)
          .timeout(const Duration(seconds: 10));

      if (kDebugMode) print('[ARCX] getWallet: ${response.statusCode}');
      if (response.statusCode == 200) {
        if (kDebugMode) print('[ARCX] getWallet response: ${response.body}');
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] getWallet error: $e');
      return null;
    }
  }

  /// Deposit INR into the ARCX wallet.
  Future<Map<String, dynamic>?> deposit(double amountInr) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/wallet/deposit/'),
            headers: headers,
            body: jsonEncode({'amount_inr': amountInr}),
          )
          .timeout(const Duration(seconds: 15));

      if (kDebugMode) print('[ARCX] deposit: ${response.statusCode} ${response.body}');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] deposit error: $e');
      return null;
    }
  }

  // ───────────────────── Treasury ──────────────────────

  /// Get the current ARCX price and treasury data (public, no auth needed).
  Future<Map<String, dynamic>?> getTreasury() async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/treasury/'),
            headers: {'Content-Type': 'application/json'},
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] getTreasury error: $e');
      return null;
    }
  }

  // ───────────────────── Oracle ──────────────────────

  /// Get live market prices (public)
  Future<Map<String, dynamic>?> getLivePrices() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/oracle/prices/'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] getLivePrices error: $e');
      return null;
    }
  }

  /// Get a 30-second locked quote for withdraw/send
  Future<Map<String, dynamic>?> getQuote(String action) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .get(Uri.parse('$baseUrl/oracle/quote/?action=$action'), headers: headers)
          .timeout(const Duration(seconds: 10));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] getQuote error: $e');
      return null;
    }
  }

  // ───────────────────── Transactions ──────────────────────

  /// Deposit INR to mint ARCX tokens
  Future<Map<String, dynamic>?> depositInr(double amountInr, {String? pin}) async {
    try {
      final headers = await _authHeaders();
      Map<String, dynamic> bodyMap = {'amount_inr': amountInr};
      // Hash PIN with SHA256 to match backend
      if (pin != null) {
        final hashedPin = sha256.convert(utf8.encode(pin)).toString();
        bodyMap['pin'] = hashedPin;
      }
      final response = await http
          .post(
            Uri.parse('$baseUrl/tx/deposit/'),
            headers: headers,
            body: jsonEncode(bodyMap),
          )
          .timeout(const Duration(seconds: 30));

      if (kDebugMode) print('[ARCX] depositInr: ${response.statusCode} ${response.body}');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] depositInr error: $e');
      return null;
    }
  }

  /// Withdraw ARCX to get INR
  Future<Map<String, dynamic>?> withdraw(double arcxAmount, String quoteId) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/tx/withdraw/'),
            headers: headers,
            body: jsonEncode({'arcx_amount': arcxAmount, 'quote_id': quoteId}),
          )
          .timeout(const Duration(seconds: 30));

      if (kDebugMode) print('[ARCX] withdraw: ${response.statusCode} ${response.body}');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] withdraw error: $e');
      return null;
    }
  }

  /// Send ARCX to another user
  Future<Map<String, dynamic>?> sendArcx(String recipientEmail, double arcxAmount, String quoteId) async {
    try {
      final headers = await _authHeaders();
      final response = await http
          .post(
            Uri.parse('$baseUrl/tx/send/'),
            headers: headers,
            body: jsonEncode({
              'recipient_email': recipientEmail,
              'arcx_amount': arcxAmount,
              'quote_id': quoteId,
            }),
          )
          .timeout(const Duration(seconds: 30));

      if (kDebugMode) print('[ARCX] sendArcx: ${response.statusCode} ${response.body}');
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return null;
    } catch (e) {
      if (kDebugMode) print('[ARCX] sendArcx error: $e');
      return null;
    }
  }
}
