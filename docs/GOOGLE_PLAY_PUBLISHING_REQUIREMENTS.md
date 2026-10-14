# Google Play Publishing Requirements: Android and PC

**Reference date:** October 14, 2026

This document summarizes the main requirements and decisions for publishing an app to Google Play. Google updates its policies and technical requirements, so confirm the linked Play Console guidance before submitting a release.

## Important distinction: Android, PC, and Windows

Google Play is primarily a store for Android apps. A Windows desktop installer (`.exe` or MSIX) cannot be submitted as an ordinary Google Play app.

For PC distribution through Google, the relevant product is **Google Play Games on PC**, which distributes supported Android games to Windows PCs. It is not a general Windows software store. A web app can also be used on PC through a browser without being listed on Google Play.

| Desired distribution | What is submitted |
| --- | --- |
| Android phones and tablets | An Android app bundle (`.aab`) in Play Console |
| Windows PCs through Google Play Games | An Android game that is compatible with Google Play Games on PC |
| Windows desktop software | A Windows app distributed through a PC-oriented channel such as Microsoft Store, Steam, or the developer's website |
| Browser-based PC experience | The website, hosted and accessed through a browser |

## Android app publishing checklist

### Developer account and app setup

- Create a Google Play Console developer account and complete any identity, contact, and device verification requested for the account.
- Create the app in Play Console. Choose its app/game and free/paid status, default language, display name, and a support contact email.
- Choose the Android application ID/package name carefully. Google treats it as unique and permanent; it cannot be reused after deletion.
- Accept the required developer, export-law, and Play App Signing terms.

### Build and release

- Upload a signed Android App Bundle (`.aab`). New Play apps use Android App Bundles, and Play App Signing manages the app's signing key for distribution.
- Use a unique, increasing version code for each release.
- **Target API level:** As of August 31, 2026, new phone/tablet apps and app updates must target **Android 16 (API level 36) or higher**. Form factors such as Wear OS, Android TV, Android Automotive OS, and Android XR have separate requirements.
- Test the app on supported Android versions and device sizes. Ensure it is stable, usable, and does not contain broken or misleading functionality.
- If sign-in is required, provide working reviewer credentials and instructions in Play Console so reviewers can access gated functionality.

### Store listing and declarations

- Complete the store listing: app name and descriptions, app icon, screenshots and other required graphics, category, support contact details, and countries/regions where it will be available.
- Complete the content-rating questionnaire and declare the target audience. Additional Families requirements apply if children are included in the target audience.
- Declare whether the app contains ads and complete any other declarations that apply to its features, such as sensitive permissions, health or financial functionality, or government affiliation.
- Complete the **Data safety** form accurately, including data collected or shared by third-party SDKs. Google requires the form for apps on closed, open, and production tracks; apps exclusively on an internal testing track are exempt.
- Provide a public privacy policy. Google requires a privacy policy even when the app declares that it collects no user data. Ensure the policy and Data safety answers match the app's actual behavior, including its SDKs and backend services.
- If users can create accounts in the app, review Google's account-deletion requirements. Apps in scope need a way to request account deletion both from within the app and through a web resource linked from the Play listing.
- Request only permissions that are necessary, and satisfy any additional Play policy and declaration requirements for restricted or sensitive permissions.

### Testing gate for some personal accounts

If the developer account is a **personal account created after November 13, 2023**, Google requires a closed test before production access:

- At least **12 testers** must be opted in to the closed test continuously for at least **14 days** immediately before the production-access application.
- Publish a closed-test release, add testers by email list or Google Group, and share the Play opt-in link. Testers need a Google account, must opt in, and should install and exercise the app.
- Keep the closed test active, collect and review feedback, and address issues. Google may consider tester engagement; meeting the minimum count and duration does not guarantee production access.
- After the test, apply for production access from the app dashboard and answer questions about the test, app, feedback, and readiness.

This specific 12-tester requirement depends on account type and creation date; check the current Play Console dashboard for the account's actual requirements.

## PC distribution options

### Google Play Games on PC

- This is for compatible **Android games**, not arbitrary Windows desktop apps.
- Google Play Console's app-creation guidance says free games appear on Google Play Games on PC by default; paid games must be released there separately. Availability and PC compatibility still depend on Google's current program requirements and the app's configuration.
- Design and test the game for PC use: keyboard and mouse input, large screens and resizable windows, clear controls, and reliable behavior in the Google Play Games on PC environment.
- Check Play Console and current Google Play Games on PC developer guidance for any game-specific compatibility or eligibility checks before planning a PC release. The PC route is separate from a Windows `.exe` release.

### Windows desktop app

A Windows app must be distributed through a Windows-compatible channel, for example Microsoft Store, Steam, or the developer's own website. Google Play's Android App Bundle, Android target API, and personal-account closed-test rules do not directly apply to a standalone Windows installer.

## How this relates to the Chess AI app

The repository describes Chess AI as a web application with a mobile-optimized web interface and backend services. That web project is not itself an Android App Bundle. To publish it on Android, the project would need an Android app/client package (native or an appropriate web-app wrapper) that connects securely to the hosted services and satisfies Play policies. The existing browser experience can serve PC users as a website; a Windows desktop release would be a separate packaging and distribution decision.

## Official references

- [Create and set up your app](https://support.google.com/googleplay/android-developer/answer/9859152)
- [Target API level requirements](https://support.google.com/googleplay/android-developer/answer/11926878)
- [Testing requirements for new personal developer accounts](https://support.google.com/googleplay/android-developer/answer/14151465)
- [Set up a closed, open, or internal test](https://support.google.com/googleplay/android-developer/answer/9845334)
- [Google Play Data safety](https://support.google.com/googleplay/android-developer/answer/10787469)
- [Prepare your app for review](https://support.google.com/googleplay/android-developer/answer/9859455)
- [Google Play Developer Program Policies](https://play.google/developer-content-policy/)
- [Google Play Games on PC overview](https://developer.android.com/games/playgames/overview)