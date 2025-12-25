# Mobile Testing Protocol - PC Recommendation System

## 🚨 DEPLOYMENT BLOCKED UNTIL ALL TESTS PASS

This document provides the complete testing protocol for mobile authentication. **Deployment is blocked** until all mobile browsers pass these tests.

## 📱 TEST ENVIRONMENT SETUP

### Prerequisites
- [ ] Backend running: `docker-compose up backend`
- [ ] Frontend configured with correct IP: `frontend/.env.local` → `REACT_APP_API_BASE_URL=http://192.168.0.105:8000/api/v1`
- [ ] Mobile device connected to same WiFi network as development machine
- [ ] Current IP address verified: `192.168.0.105` (run `ipconfig` to confirm)

### Test URLs
- **Backend Health**: `http://192.168.0.105:8000/api/v1/health`
- **CORS Test Tool**: `http://192.168.0.105:8000/mobile_cors_test.html`
- **Frontend App**: `http://192.168.0.105:3000`
- **Swagger Docs**: `http://192.168.0.105:8000/docs`

## 🧪 BROWSER-SPECIFIC TESTING PROTOCOL

### 1. CHROME MOBILE (Android/iOS)

#### Pre-Test Setup
- [ ] Clear browser cache and cookies
- [ ] Disable any ad blockers or security extensions
- [ ] Ensure JavaScript is enabled
- [ ] Check that "Block third-party cookies" is OFF

#### Test Steps
1. **Open CORS Test Tool**
   - Navigate to: `http://192.168.0.105:8000/mobile_cors_test.html`
   - [ ] Page loads without errors
   - [ ] "Test Token Storage" shows ✅ localStorage working
   - [ ] "Test Health Check" returns status 200

2. **Test Authentication**
   - [ ] Click "Test Signup" → Should return status 201 or 400 (validation error)
   - [ ] Click "Test Login" → Should return status 401 (user doesn't exist) or 200 (success)
   - [ ] Check browser console → No CORS errors
   - [ ] Check Network tab → No failed preflight requests

3. **Test Full Application**
   - Navigate to: `http://192.168.0.105:3000`
   - [ ] Frontend loads successfully
   - [ ] Try to signup with test credentials
   - [ ] Signup completes without errors
   - [ ] Try to login with created credentials
   - [ ] Login succeeds and redirects to dashboard
   - [ ] Check Application > Local Storage → Tokens are stored

#### Expected Chrome Behavior
- ✅ Should work perfectly (Chrome has best CORS support)
- ✅ localStorage fully functional
- ✅ All authentication flows work
- ✅ No security warnings or blocks

#### Chrome-Specific Issues & Fixes
- **Issue**: "net::ERR_BLOCKED_BY_CLIENT" → Disable ad blockers
- **Issue**: Mixed content warnings → Ensure all URLs use HTTP (development)
- **Issue**: CORS preflight fails → Check network connectivity

---

### 2. ANDROID BROWSER (Samsung Internet, etc.)

#### Pre-Test Setup
- [ ] Clear browser cache and data
- [ ] Enable "Allow cookies" in privacy settings
- [ ] Disable "Block pop-ups" if enabled
- [ ] Ensure "JavaScript" is enabled

#### Test Steps
1. **CORS Test Tool**
   - [ ] Page loads and all tests pass
   - [ ] localStorage test shows ✅
   - [ ] No "SecurityError" or "QuotaExceededError"

2. **Authentication Tests**
   - [ ] Signup works without "CORS error" or "Network error"
   - [ ] Login completes successfully
   - [ ] Tokens stored in localStorage

3. **Full App Test**
   - [ ] Complete signup/login flow works
   - [ ] No unexpected redirects or errors
   - [ ] Authentication persists across page refreshes

#### Expected Android Browser Behavior
- ✅ Should work well (similar to Chrome)
- ✅ localStorage available
- ⚠️ May have stricter cookie policies than Chrome

#### Android Browser Issues & Fixes
- **Issue**: "localStorage is not available" → Clear browser data and restart
- **Issue**: "Failed to fetch" → Check WiFi connection and IP address
- **Issue**: Cookie warnings → Ensure cookies are enabled

---

### 3. iOS SAFARI (iPhone/iPad)

#### Pre-Test Setup
- [ ] Clear History and Website Data: Settings > Safari > Clear History and Website Data
- [ ] Disable "Prevent Cross-Site Tracking": Settings > Safari > Prevent Cross-Site Tracking (OFF)
- [ ] Enable "Block All Cookies": Settings > Safari > Block All Cookies (OFF)
- [ ] Ensure "JavaScript" is enabled: Settings > Safari > Advanced > JavaScript (ON)

#### Test Steps
1. **CORS Test Tool**
   - [ ] Page loads (Safari may show security warnings - proceed)
   - [ ] localStorage test passes
   - [ ] Health check returns 200

2. **Authentication Tests**
   - [ ] **CRITICAL**: iOS Safari often blocks CORS requests
   - [ ] Check for "CORS error" or "Origin not allowed"
   - [ ] If blocked, check Safari settings above
   - [ ] Try private browsing mode if public mode fails

3. **Full App Test**
   - [ ] If CORS works, complete authentication flow
   - [ ] Check for any iOS-specific redirects or blocks

#### Expected iOS Safari Behavior
- ⚠️ **MOST LIKELY TO FAIL** - Safari has strict CORS policies
- ⚠️ May require "Prevent Cross-Site Tracking" disabled
- ⚠️ Private browsing may work better than regular browsing
- ✅ If settings are correct, should work like other browsers

#### iOS Safari Critical Issues & Fixes
- **Issue**: "CORS preflight failed" → Disable "Prevent Cross-Site Tracking"
- **Issue**: "Origin not allowed" → Check Safari privacy settings
- **Issue**: "localStorage blocked" → Clear website data and try private mode
- **Issue**: "Failed to load resource" → Check network settings and IP

---

## 🔍 DIAGNOSTIC CHECKLIST

### For Each Browser Test

#### Network Tab Analysis
- [ ] Open DevTools → Network tab
- [ ] Look for failed requests (red entries)
- [ ] Check preflight OPTIONS requests
- [ ] Verify CORS headers in response headers

#### Console Error Analysis
- [ ] Open DevTools → Console tab
- [ ] Look for CORS-related errors:
  - `Access to XMLHttpRequest blocked by CORS policy`
  - `Response to preflight request doesn't pass access control check`
  - `No 'Access-Control-Allow-Origin' header`
- [ ] Check for localStorage errors:
  - `SecurityError: localStorage is not available`
  - `QuotaExceededError`

#### Application Storage Check
- [ ] DevTools → Application → Local Storage
- [ ] Verify tokens are stored after successful login:
  - `accessToken`: JWT token present
  - `refreshToken`: JWT token present
  - `user`: JSON object with user data

### HTTP vs HTTPS Considerations
- [ ] **Development**: All URLs should be HTTP (not HTTPS)
- [ ] **Production**: All URLs should be HTTPS
- [ ] **Mixed Content**: Ensure no HTTP requests from HTTPS pages

## 📊 TEST RESULTS TEMPLATE

### Browser: [Chrome Mobile / Android Browser / iOS Safari]
### Device: [Android Phone / iPhone / iPad]
### OS Version: [Android 12 / iOS 15.2]

#### CORS Test Tool Results
- Health Check: ✅ PASS / ❌ FAIL
- Token Storage: ✅ PASS / ❌ FAIL
- Signup Test: ✅ PASS / ❌ FAIL
- Login Test: ✅ PASS / ❌ FAIL

#### Full App Test Results
- Frontend Loads: ✅ PASS / ❌ FAIL
- Signup Works: ✅ PASS / ❌ FAIL
- Login Works: ✅ PASS / ❌ FAIL
- Tokens Stored: ✅ PASS / ❌ FAIL

#### Issues Observed
- [ ] CORS errors in console
- [ ] Network request failures
- [ ] localStorage not working
- [ ] Authentication flow broken
- [ ] Other: ________________

#### Console Errors
```
[Paste any relevant console errors here]
```

#### Network Tab Issues
```
[Paste any failed network requests here]
```

## 🚨 DEPLOYMENT CRITERIA

### ✅ **ALL BROWSERS MUST PASS**
- [ ] Chrome Mobile: All tests pass
- [ ] Android Browser: All tests pass
- [ ] iOS Safari: All tests pass

### ✅ **NO CRITICAL ISSUES**
- [ ] No CORS errors blocking authentication
- [ ] No localStorage failures
- [ ] No network connectivity issues
- [ ] No browser-specific blocks

### ✅ **FULL FUNCTIONALITY**
- [ ] Signup completes successfully
- [ ] Login works and stores tokens
- [ ] Authentication persists
- [ ] Protected routes accessible

## 🛠️ TROUBLESHOOTING GUIDES

### If CORS Fails on iOS Safari
1. Settings → Safari → Prevent Cross-Site Tracking → OFF
2. Settings → Safari → Block All Cookies → OFF
3. Clear History and Website Data
4. Try Private Browsing mode
5. Restart Safari completely

### If localStorage Fails
1. Clear browser data and cache
2. Check if browser is in private/incognito mode
3. Verify no browser extensions blocking storage
4. Try different browser

### If Network Requests Fail
1. Verify IP address hasn't changed
2. Check WiFi connection stability
3. Ensure backend is running and accessible
4. Try different browser or device

## 📞 SUPPORT CHECKLIST

If issues persist after following this protocol:
- [ ] All browsers tested according to this guide
- [ ] Screenshots of console errors provided
- [ ] Network tab screenshots included
- [ ] Device and browser versions documented
- [ ] Backend logs checked for errors

---

**REMINDER: Deployment is BLOCKED until all mobile browsers pass these tests successfully.**