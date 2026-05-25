import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:google_fonts/google_fonts.dart';
import 'auth_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  // iOS Minimal Dark Mode Palette
  static const Color bgColor = Color(0xFF000000);
  static const Color surfaceColor = Color(0xFF1C1C1E);
  static const Color cardColor = Color(0xFF1C1C1E);
  static const Color arcxWhite = Color(0xFFFFFFFF);
  static const Color accentGold = Color(0xFFFFD60A); // iOS Yellow
  static const Color accentGoldLight = Color(0xFFFFD60A);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: Column(
          children: [
            // Progress Indicators
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildIndicator(_currentPage == 0 ? accentGold : arcxWhite.withValues(alpha: 0.15)),
                const SizedBox(width: 8),
                _buildIndicator(_currentPage == 1 ? accentGold : arcxWhite.withValues(alpha: 0.15)),
                const SizedBox(width: 8),
                _buildIndicator(_currentPage == 2 ? accentGold : arcxWhite.withValues(alpha: 0.15)),
              ],
            ),
            const SizedBox(height: 32),

            // Swipeable Pages
            Expanded(
              child: PageView(
                controller: _pageController,
                onPageChanged: (index) {
                  setState(() {
                    _currentPage = index;
                  });
                },
                children: [
                  _buildPage1(),
                  _buildPage2(),
                  _buildPage3(),
                ],
              ),
            ),

            // Bottom Controls
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32.0),
              child: ElevatedButton(
                onPressed: () {
                  if (_currentPage < 2) {
                    _pageController.nextPage(
                      duration: const Duration(milliseconds: 400),
                      curve: Curves.easeInOut,
                    );
                  } else {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const AuthScreen()),
                    );
                  }
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: arcxWhite,
                  minimumSize: const Size(double.infinity, 56),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 0,
                ),
                child: Text(
                  _currentPage == 2 ? 'Get Started' : 'Continue',
                  style: GoogleFonts.inter(
                    color: bgColor,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Back Button
            SizedBox(
              height: 44,
              child: _currentPage > 0
                  ? TextButton(
                      onPressed: () {
                        _pageController.previousPage(
                          duration: const Duration(milliseconds: 400),
                          curve: Curves.easeInOut,
                        );
                      },
                      child: Text(
                        'Back',
                        style: GoogleFonts.inter(
                          color: arcxWhite.withValues(alpha: 0.5),
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    )
                  : null,
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildIndicator(Color color) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      width: _currentPage == 0 ? 32 : (_currentPage == 1 ? 24 : 16),
      height: 4,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(4),
      ),
    );
  }

  // --- SLIDE 1: What is ARCX ---
  Widget _buildPage1() {
    return Column(
      children: [
        // Top: Logo + Badge
        Expanded(
          flex: 5,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo with glow effect
                Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        accentGold.withValues(alpha: 0.3),
                        accentGold.withValues(alpha: 0.0),
                      ],
                      stops: const [0.3, 1.0],
                    ),
                  ),
                  child: Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          accentGold,
                          accentGoldLight,
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: accentGold.withValues(alpha: 0.4),
                          blurRadius: 30,
                          spreadRadius: 5,
                        ),
                      ],
                    ),
                    child: Center(
                      child: Text(
                        'AX',
                        style: GoogleFonts.playfairDisplay(
                          color: bgColor,
                          fontSize: 42,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                // Badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                  decoration: BoxDecoration(
                    color: surfaceColor,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: accentGold.withValues(alpha: 0.2),
                      width: 1,
                    ),
                  ),
                  child: Text(
                    'Yield-Bearing Currency',
                    style: GoogleFonts.inter(
                      color: accentGold,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),

        // Bottom: Text
        Expanded(
          flex: 3,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Meet ARCX',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.playfairDisplay(
                    color: arcxWhite,
                    fontSize: 36,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'A global financial engine that beats inflation. Your money grows automatically — just by holding it.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.7),
                    fontSize: 15,
                    fontWeight: FontWeight.w400,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  // --- SLIDE 2: Asset Allocation ---
  Widget _buildPage2() {
    return Column(
      children: [
        // Top: Asset Visualization
        Expanded(
          flex: 5,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'INSTITUTIONAL-GRADE',
                    style: GoogleFonts.inter(
                      color: accentGold,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 2,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Asset Backing',
                    style: GoogleFonts.playfairDisplay(
                      color: arcxWhite,
                      fontSize: 28,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 36),

                  // Allocation visual with icons
                  _buildAssetCard(CupertinoIcons.chart_bar_alt_fill, 'Stocks', '40%', const Color(0xFF30D158)), // iOS Green
                  const SizedBox(height: 12),
                  _buildAssetCard(CupertinoIcons.doc_text_fill, 'Bonds', '30%', const Color(0xFF0A84FF)), // iOS Blue
                  const SizedBox(height: 12),
                  _buildAssetCard(CupertinoIcons.star_fill, 'Gold', '20%', accentGold),
                  const SizedBox(height: 12),
                  _buildAssetCard(CupertinoIcons.money_dollar_circle_fill, 'Cash', '10%', arcxWhite.withValues(alpha: 0.5)),
                ],
              ),
            ),
          ),
        ),

        // Bottom: Text
        Expanded(
          flex: 2,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Mathematically Backed',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.playfairDisplay(
                    color: arcxWhite,
                    fontSize: 26,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Every ARCX is backed by real assets. Stocks, bonds, gold — you own a piece of the global economy.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.6),
                    fontSize: 14,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAssetCard(IconData icon, String label, String percentage, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16), // Apple standard corner radius
        border: Border.all(
          color: arcxWhite.withValues(alpha: 0.05),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: arcxWhite.withValues(alpha: 0.9),
                fontSize: 16,
                fontWeight: FontWeight.w500,
                letterSpacing: -0.2,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              percentage,
              style: GoogleFonts.inter(
                color: color,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- SLIDE 3: Why Use ARCX ---
  Widget _buildPage3() {
    return Column(
      children: [
        // Top: Feature Cards
        Expanded(
          flex: 5,
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  _buildFeatureCard(
                    icon: CupertinoIcons.graph_circle,
                    iconColor: const Color(0xFF34C759),
                    title: 'Beat Inflation',
                    subtitle: 'Your wealth grows automatically, every single day',
                  ),
                  const SizedBox(height: 14),
                  _buildFeatureCard(
                    icon: CupertinoIcons.shield_fill,
                    iconColor: const Color(0xFF0A84FF),
                    title: 'Zero Volatility',
                    subtitle: 'Gold & bonds protect you from market crashes',
                  ),
                  const SizedBox(height: 14),
                  _buildFeatureCard(
                    icon: CupertinoIcons.creditcard_fill,
                    iconColor: accentGold,
                    title: 'Spend Like Cash',
                    subtitle: 'Use anywhere UPI is accepted — instant & free',
                  ),
                ],
              ),
            ),
          ),
        ),

        // Bottom: CTA
        Expanded(
          flex: 2,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Start Your Journey',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.playfairDisplay(
                    color: arcxWhite,
                    fontSize: 28,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Join thousands growing their wealth with ARCX.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.5),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFeatureCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: arcxWhite.withValues(alpha: 0.05),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: iconColor, size: 26),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(
                    color: arcxWhite,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: GoogleFonts.inter(
                    color: arcxWhite.withValues(alpha: 0.45),
                    fontSize: 13,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}