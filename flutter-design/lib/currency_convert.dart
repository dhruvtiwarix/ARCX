import 'package:flutter/cupertino.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return CupertinoApp(
      
      home: CupertinoPageScaffold(
        navigationBar: CupertinoNavigationBar(
          backgroundColor: CupertinoColors.systemGroupedBackground,
          transitionBetweenRoutes: false,
          border: null,
          padding: EdgeInsetsDirectional.only(start: 20, end: 20),
          leading: Text('ARCX'),
          trailing: Icon(CupertinoIcons.shopping_cart),
        ),
        child: Center(
          child: Text('hello!!'),
        ),
      ),
    );
  }
}