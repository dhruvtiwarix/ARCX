import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_service.dart';
import '../../../core/widgets/glass_container.dart';

class KycScreen extends ConsumerStatefulWidget {
  final VoidCallback? onVerificationComplete;

  const KycScreen({super.key, required this.onVerificationComplete});

  @override
  ConsumerState<KycScreen> createState() => _KycScreenState();
}

class _KycScreenState extends ConsumerState<KycScreen> {
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color accentGold = Color(0xFFFFD60A);
  // static const Color accentPurple = Color(0xFFA855F7);
  static const Color textMuted = Color(0xFF8E8E93);
  static const Color arcxGreen = Color(0xFF30D158);

  final ApiService _apiService = ApiService();

  // Current step (0-4)
  int _currentStep = 0;
  bool _isLoading = false;
  String? _error;

  // Form Controllers
  final _formKey = GlobalKey<FormState>();

  // Step 1: Personal Details
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _phoneController = TextEditingController();
  DateTime? _selectedDob;
  String _selectedGender = 'M';

  // Step 2: Address
  final _addressLine1Controller = TextEditingController();
  final _addressLine2Controller = TextEditingController();
  final _cityController = TextEditingController();
  final _stateController = TextEditingController();
  final _pincodeController = TextEditingController();

  // Step 3: ID Verification
  final _panController = TextEditingController();
  final _aadhaarController = TextEditingController();

  // Step 4: ARCX PIN
  String _pin = '';
  String _confirmPin = '';
  bool _isPinConfirmStage = false;

  final List<String> _steps = [
    'Personal',
    'Address',
    'ID Verify',
    'ARCX PIN',
  ];

  @override
  void dispose() {
    _firstNameController.dispose();
    _lastNameController.dispose();
    _phoneController.dispose();
    _addressLine1Controller.dispose();
    _addressLine2Controller.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _pincodeController.dispose();
    _panController.dispose();
    _aadhaarController.dispose();
    super.dispose();
  }

  Future<void> _nextStep() async {
    if (_currentStep == 0) {
      if (_firstNameController.text.isEmpty || _phoneController.text.isEmpty) {
        _showError('Please fill all required fields');
        return;
      }
      if (_selectedDob == null) {
        _showError('Please select your date of birth');
        return;
      }
      await _submitStep1();
    } else if (_currentStep == 1) {
      if (_addressLine1Controller.text.isEmpty || _cityController.text.isEmpty || _pincodeController.text.isEmpty) {
        _showError('Please fill all required fields');
        return;
      }
      await _submitStep2();
    } else if (_currentStep == 2) {
      if (_panController.text.isEmpty || _aadhaarController.text.isEmpty) {
        _showError('Please enter PAN and Aadhaar numbers');
        return;
      }
      await _submitStep3();
    } else if (_currentStep == 3) {
      // PIN step — handled by the numpad, just complete KYC
      await _submitPin();
    }
  }

  Future<void> _submitStep1() async {
    setState(() { _isLoading = true; _error = null; });

    try {
      final success = await _apiService.submitKycStep1(
        firstName: _firstNameController.text,
        lastName: _lastNameController.text,
        dateOfBirth: _selectedDob!,
        gender: _selectedGender,
        phoneNumber: _phoneController.text,
      );
      if (success) {
        setState(() => _currentStep++);
      } else {
        _showError('Failed to save personal details');
      }
    } catch (e) {
      _showError('Failed to save personal details');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _submitStep2() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final success = await _apiService.submitKycStep2(
        addressLine1: _addressLine1Controller.text,
        addressLine2: _addressLine2Controller.text,
        city: _cityController.text,
        state: _stateController.text,
        pincode: _pincodeController.text,
      );
      if (success) {
        setState(() => _currentStep++);
      } else {
        _showError('Failed to save address details');
      }
    } catch (e) {
      _showError('Failed to save address details');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _submitStep3() async {
    setState(() { _isLoading = true; _error = null; });
    try {
      final success = await _apiService.submitKycStep3(
        panNumber: _panController.text,
        aadhaarNumber: _aadhaarController.text,
      );
      if (success) {
        setState(() => _currentStep++);
      } else {
        _showError('Failed to verify identity');
      }
    } catch (e) {
      _showError('Failed to verify identity');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _submitPin() async {
    if (_pin.length != 6) {
      _showError('Please enter a 6-digit PIN');
      return;
    }
    if (!_isPinConfirmStage) {
      setState(() => _isPinConfirmStage = true);
      return;
    }
    if (_pin != _confirmPin) {
      _showError('PINs do not match. Try again.');
      setState(() {
        _pin = '';
        _confirmPin = '';
        _isPinConfirmStage = false;
      });
      return;
    }

    setState(() { _isLoading = true; });

    final success = await _apiService.setPin(_pin);
    if (success) {
      final completeSuccess = await _apiService.completeKyc();
      if (completeSuccess) {
        setState(() { _isLoading = false; });
        _showSuccessAndComplete();
      } else {
        setState(() { _isLoading = false; });
        _showError('Failed to finalize KYC. Please try again.');
      }
    } else {
      setState(() { _isLoading = false; });
      _showError('Failed to set PIN. Please try again.');
    }
  }

  void _showError(String message) {
    setState(() => _error = message);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  void _showSuccessAndComplete() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: surfaceColor,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: arcxGreen.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.check_circle, color: arcxGreen, size: 48),
            ),
            const SizedBox(height: 20),
            Text(
              'KYC Complete!',
              style: GoogleFonts.playfairDisplay(
                color: Colors.white, fontSize: 24, fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Your account is now fully verified. You can deposit, withdraw, and transfer funds.',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: textMuted, fontSize: 14),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pop(context);
                  widget.onVerificationComplete?.call();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: accentGold,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: Text('Continue', style: GoogleFonts.inter(
                  color: Colors.black, fontWeight: FontWeight.w600,
                )),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _selectDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: _selectedDob ?? DateTime(2000),
      firstDate: DateTime(1950),
      lastDate: DateTime.now().subtract(const Duration(days: 365 * 18)),
      builder: (context, child) {
        return Theme(
          data: ThemeData.dark().copyWith(
            colorScheme: const ColorScheme.dark(
              primary: accentGold,
              surface: surfaceColor,
            ),
          ),
          child: child!,
        );
      },
    );
    if (date != null) {
      setState(() => _selectedDob = date);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Column(
          children: [
            // Progress Header
            _buildHeader(),

            // Step Content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: _buildStepContent(),
              ),
            ),

            // Bottom Button
            _buildBottomButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Back button
          Row(
            children: [
              if (_currentStep > 0)
                GestureDetector(
                  onTap: () => setState(() => _currentStep--),
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: surfaceColor,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 18),
                  ),
                ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _getStepTitle(),
                  style: GoogleFonts.playfairDisplay(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Step Indicators
          Row(
            children: List.generate(5, (index) {
              final isCompleted = index < _currentStep;
              final isCurrent = index == _currentStep;
              return Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 2),
                  height: 4,
                  decoration: BoxDecoration(
                    color: isCompleted || isCurrent
                        ? accentGold
                        : Colors.white.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: _steps.asMap().entries.map((e) {
              final isCompleted = e.key < _currentStep;
              final isCurrent = e.key == _currentStep;
              return Text(
                e.value,
                style: GoogleFonts.inter(
                  color: isCompleted || isCurrent ? accentGold : textMuted,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  String _getStepTitle() {
    switch (_currentStep) {
      case 0: return 'Personal Details';
      case 1: return 'Your Address';
      case 2: return 'ID Verification';
      case 3: return _isPinConfirmStage ? 'Confirm PIN' : 'Set ARCX PIN';
      default: return 'KYC';
    }
  }

  Widget _buildStepContent() {
    switch (_currentStep) {
      case 0: return _buildStep1();
      case 1: return _buildStep2();
      case 2: return _buildStep3();
      case 3: return _buildPinStep();
      default: return const SizedBox();
    }
  }

  Widget _buildStep1() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Let\'s get to know you',
          style: GoogleFonts.inter(color: textMuted, fontSize: 14),
        ),
        const SizedBox(height: 24),

        _buildTextField('First Name', _firstNameController, TextCapitalization.words),
        const SizedBox(height: 16),
        _buildTextField('Last Name', _lastNameController, TextCapitalization.words),
        const SizedBox(height: 16),

        // Date of Birth
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'DATE OF BIRTH',
            style: GoogleFonts.inter(
              color: textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
        ),
        GestureDetector(
          onTap: _selectDate,
          child: GlassContainer(
            borderRadius: 16,
            blur: 20,
            opacity: 0.06,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            child: Row(
              children: [
                Icon(CupertinoIcons.calendar, color: textMuted, size: 20),
                const SizedBox(width: 12),
                Text(
                  _selectedDob != null
                      ? DateFormat('dd MMMM yyyy').format(_selectedDob!)
                      : 'Select Date of Birth',
                  style: GoogleFonts.inter(
                    color: _selectedDob != null ? Colors.white : Colors.white.withValues(alpha: 0.3),
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        // Gender Selection
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            'GENDER',
            style: GoogleFonts.inter(
              color: textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
        ),
        SizedBox(
          width: double.infinity,
          child: CupertinoSlidingSegmentedControl<String>(
            backgroundColor: surfaceColor,
            thumbColor: Colors.white.withValues(alpha: 0.15),
            groupValue: _selectedGender,
            onValueChanged: (String? value) {
              if (value != null) {
                setState(() => _selectedGender = value);
              }
            },
            children: {
              'M': Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text('Male', style: GoogleFonts.inter(color: _selectedGender == 'M' ? Colors.white : textMuted, fontSize: 14))),
              'F': Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text('Female', style: GoogleFonts.inter(color: _selectedGender == 'F' ? Colors.white : textMuted, fontSize: 14))),
              'O': Padding(padding: const EdgeInsets.symmetric(vertical: 12), child: Text('Other', style: GoogleFonts.inter(color: _selectedGender == 'O' ? Colors.white : textMuted, fontSize: 14))),
            },
          ),
        ),
        const SizedBox(height: 16),

        _buildTextField('Mobile Number', _phoneController, TextCapitalization.none, keyboardType: TextInputType.phone, prefix: '+91 '),
        const SizedBox(height: 40),
      ],
    );
  }

  Widget _buildStep2() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Where do you live?',
          style: GoogleFonts.inter(color: textMuted, fontSize: 14),
        ),
        const SizedBox(height: 24),

        _buildTextField('Address Line 1', _addressLine1Controller, TextCapitalization.words, hint: 'House No., Street Name'),
        const SizedBox(height: 16),
        _buildTextField('Address Line 2 (Optional)', _addressLine2Controller, TextCapitalization.words, hint: 'Landmark, Area'),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(child: _buildTextField('City', _cityController, TextCapitalization.words)),
            const SizedBox(width: 16),
            Expanded(child: _buildTextField('State', _stateController, TextCapitalization.words)),
          ],
        ),
        const SizedBox(height: 16),
        _buildTextField('PIN Code', _pincodeController, TextCapitalization.none, keyboardType: TextInputType.number, hint: '6-digit'),
        const SizedBox(height: 40),
      ],
    );
  }

  Widget _buildStep3() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Verify your identity',
          style: GoogleFonts.inter(color: textMuted, fontSize: 14),
        ),
        const SizedBox(height: 24),

        // PAN Card
        _buildTextField('PAN Card Number', _panController, TextCapitalization.characters, keyboardType: TextInputType.text, hint: 'ABCDE1234F', capitalize: true),
        const SizedBox(height: 8),
        Text(
          '10-character PAN number (e.g., ABCDE1234F)',
          style: GoogleFonts.inter(color: textMuted, fontSize: 11),
        ),
        const SizedBox(height: 24),

        // Aadhaar
        _buildTextField('Aadhaar Number', _aadhaarController, TextCapitalization.none, keyboardType: TextInputType.number, hint: '12-digit', maxLength: 12),
        const SizedBox(height: 8),
        Text(
          '12-digit Aadhaar number (e.g., 123456789012)',
          style: GoogleFonts.inter(color: textMuted, fontSize: 11),
        ),
        const SizedBox(height: 24),

        // Info Box
        GlassContainer(
          borderRadius: 12,
          padding: const EdgeInsets.all(16),
          blur: 10,
          opacity: 0.05,
          child: Row(
            children: [
              const Icon(Icons.info_outline, color: accentGold, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Your ID details are encrypted and stored securely as per RBI guidelines.',
                  style: GoogleFonts.inter(color: textMuted, fontSize: 12),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 40),
      ],
    );
  }



  Widget _buildPinStep() {
    final currentPin = _isPinConfirmStage ? _confirmPin : _pin;
    final subtitle = _isPinConfirmStage
        ? 'Re-enter your PIN to confirm'
        : 'This PIN secures all your ARCX transactions';

    return Column(
      children: [
        const SizedBox(height: 20),
        // Shield icon
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: accentGold.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(CupertinoIcons.lock_shield, color: accentGold, size: 28),
        ),
        const SizedBox(height: 16),
        Text(
          subtitle,
          style: GoogleFonts.inter(color: textMuted, fontSize: 14),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),

        // PIN Dots
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(6, (index) {
            final isFilled = index < currentPin.length;
            return AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              margin: const EdgeInsets.symmetric(horizontal: 8),
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isFilled ? accentGold : Colors.white.withValues(alpha: 0.15),
                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
            );
          }),
        ),
        const SizedBox(height: 36),

        // Numpad
        _buildPinNumpad(),
        const SizedBox(height: 20),
      ],
    );
  }

  void _onPinKeyTap(String key) {
    setState(() {
      if (_isPinConfirmStage) {
        if (key == 'delete') {
          if (_confirmPin.isNotEmpty) _confirmPin = _confirmPin.substring(0, _confirmPin.length - 1);
        } else if (_confirmPin.length < 6) {
          _confirmPin += key;
        }
      } else {
        if (key == 'delete') {
          if (_pin.isNotEmpty) _pin = _pin.substring(0, _pin.length - 1);
        } else if (_pin.length < 6) {
          _pin += key;
        }
      }
    });
  }

  Widget _buildPinNumpad() {
    final keys = [
      ['1', '2', '3'],
      ['4', '5', '6'],
      ['7', '8', '9'],
      ['', '0', 'delete'],
    ];

    return Column(
      children: keys.map((row) {
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: row.map((key) {
              if (key.isEmpty) return const SizedBox(width: 64, height: 48);
              final isDelete = key == 'delete';
              return GestureDetector(
                onTap: () => _onPinKeyTap(key),
                child: Container(
                  width: 64,
                  height: 48,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.05),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  alignment: Alignment.center,
                  child: isDelete
                      ? Icon(CupertinoIcons.delete_left, color: Colors.white.withValues(alpha: 0.7), size: 20)
                      : Text(key, style: GoogleFonts.inter(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w500)),
                ),
              );
            }).toList(),
          ),
        );
      }).toList(),
    );
  }
  Widget _buildTextField(String label, TextEditingController controller, TextCapitalization capitalization, {TextInputType? keyboardType, String? hint, String? prefix, int? maxLength, bool capitalize = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 8),
          child: Text(
            label.toUpperCase(),
            style: GoogleFonts.inter(
              color: textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
        ),
        GlassContainer(
          borderRadius: 16,
          blur: 20,
          opacity: 0.06,
          child: CupertinoTextField(
            controller: controller,
            style: GoogleFonts.inter(color: Colors.white, fontSize: 16),
            keyboardType: keyboardType,
            textCapitalization: capitalize ? TextCapitalization.characters : capitalization,
            maxLength: maxLength,
            placeholder: hint ?? label,
            placeholderStyle: GoogleFonts.inter(color: Colors.white.withValues(alpha: 0.2), fontSize: 16),
            prefix: prefix != null
                ? Padding(
                    padding: const EdgeInsets.only(left: 16),
                    child: Text(prefix, style: GoogleFonts.inter(color: textMuted, fontSize: 16)),
                  )
                : const SizedBox(width: 16), // Indent for the text
            padding: const EdgeInsets.symmetric(horizontal: 0, vertical: 16),
            decoration: null, // Remove default border
          ),
        ),
      ],
    );
  }



  Widget _buildBottomButton() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: SizedBox(
        width: double.infinity,
        height: 56,
        child: ElevatedButton(
          onPressed: _isLoading ? null : _nextStep,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            elevation: 0,
          ),
          child: _isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2),
                )
              : Text(
                  _currentStep == 3 ? 'Complete KYC' : 'Continue',
                  style: GoogleFonts.inter(
                    color: Colors.black,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
        ),
      ),
    );
  }
}