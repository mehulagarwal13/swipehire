# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: swipe-flow.spec.ts >> Authentication >> login page renders correctly
- Location: tests\e2e\swipe-flow.spec.ts:32:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=SwipeHire')
Expected: visible
Error: strict mode violation: locator('text=SwipeHire') resolved to 2 elements:
    1) <h1 class="text-3xl font-bold text-gray-900">SwipeHire</h1> aka getByRole('heading', { name: 'SwipeHire' })
    2) <p class="text-center text-xs text-gray-400 mt-6">By continuing, you agree to SwipeHire's Terms & P…</p> aka getByText('By continuing, you agree to')

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=SwipeHire')

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e3]:
    - generic [ref=e4]:
      - img [ref=e6]
      - heading "SwipeHire" [level=1] [ref=e8]
      - paragraph [ref=e9]: India's AI-powered job platform
    - generic [ref=e10]:
      - generic [ref=e11]:
        - generic [ref=e12]:
          - text: Mobile Number
          - generic [ref=e13]:
            - text: 🇮🇳 +91
            - textbox "10-digit mobile number" [ref=e14]
        - button "Send OTP" [disabled] [ref=e15]
      - generic [ref=e16]: or
      - button "Continue with Google" [ref=e17]:
        - img [ref=e18]
        - text: Continue with Google
    - paragraph [ref=e23]: By continuing, you agree to SwipeHire's Terms & Privacy Policy
  - alert [ref=e24]
```

# Test source

```ts
  1   | /**
  2   |  * E2E test — SwipeHire swipe flow
  3   |  * Tests: login → onboarding → swipe → applications tracker
  4   |  *
  5   |  * Run: npx playwright test
  6   |  * Prerequisites: web app running on localhost:3000, AI service on localhost:8000
  7   |  */
  8   | import { test, expect, type Page } from "@playwright/test";
  9   | 
  10  | const BASE = "http://127.0.0.1:3000";
  11  | const TEST_PHONE = "9999999999";
  12  | const TEST_OTP = "123456"; // dev mode returns this
  13  | 
  14  | async function loginWithOtp(page: Page) {
  15  |   await page.goto(`${BASE}/login`);
  16  | 
  17  |   // Enter phone number
  18  |   await page.fill('input[type="tel"]', TEST_PHONE);
  19  |   await page.click('button:has-text("Send OTP")');
  20  | 
  21  |   // Wait for OTP step
  22  |   await expect(page.locator('text=Enter OTP')).toBeVisible({ timeout: 5000 });
  23  | 
  24  |   // In dev mode the OTP is shown in a toast — intercept it
  25  |   // For test stability, mock the API call
  26  |   await page.fill('input[placeholder="••••••"]', TEST_OTP);
  27  |   await page.click('button:has-text("Verify & Sign In")');
  28  | }
  29  | 
  30  | 
  31  | test.describe("Authentication", () => {
  32  |   test("login page renders correctly", async ({ page }) => {
  33  |     await page.goto(`${BASE}/login`);
> 34  |     await expect(page.locator("text=SwipeHire")).toBeVisible();
      |                                                  ^ Error: expect(locator).toBeVisible() failed
  35  |     await expect(page.locator("text=India's AI job platform")).toBeVisible();
  36  |     await expect(page.locator('input[type="tel"]')).toBeVisible();
  37  |     await expect(page.locator('button:has-text("Send OTP")')).toBeVisible();
  38  |   });
  39  | 
  40  |   test("send OTP button disabled until 10 digits entered", async ({ page }) => {
  41  |     await page.goto(`${BASE}/login`);
  42  |     const btn = page.locator('button:has-text("Send OTP")');
  43  |     await expect(btn).toBeDisabled();
  44  | 
  45  |     await page.fill('input[type="tel"]', "12345");
  46  |     await expect(btn).toBeDisabled();
  47  | 
  48  |     await page.fill('input[type="tel"]', "9876543210");
  49  |     await expect(btn).not.toBeDisabled();
  50  |   });
  51  | 
  52  |   test("shows OTP input after phone submission", async ({ page }) => {
  53  |     await page.route("**/api/v1/auth/send-otp", async (route) => {
  54  |       await route.fulfill({
  55  |         status: 200,
  56  |         contentType: "application/json",
  57  |         body: JSON.stringify({ message: "OTP sent", dev_otp: "123456" }),
  58  |       });
  59  |     });
  60  | 
  61  |     await page.goto(`${BASE}/login`);
  62  |     await page.fill('input[type="tel"]', "9876543210");
  63  |     await page.click('button:has-text("Send OTP")');
  64  | 
  65  |     await expect(page.locator('text=Enter OTP')).toBeVisible();
  66  |     await expect(page.locator('input[placeholder="••••••"]')).toBeVisible();
  67  |   });
  68  | });
  69  | 
  70  | 
  71  | test.describe("Onboarding", () => {
  72  |   test.beforeEach(async ({ page }) => {
  73  |     // Mock auth
  74  |     await page.route("**/api/v1/auth/verify-otp", async (route) => {
  75  |       await route.fulfill({
  76  |         status: 200,
  77  |         contentType: "application/json",
  78  |         body: JSON.stringify({
  79  |           access_token: "mock_token",
  80  |           refresh_token: "mock_refresh",
  81  |           user_id: "user-123",
  82  |           is_onboarded: false,
  83  |         }),
  84  |       });
  85  |     });
  86  |     await page.route("**/api/v1/auth/send-otp", async (route) => {
  87  |       await route.fulfill({ status: 200, body: JSON.stringify({ message: "OTP sent", dev_otp: "123456" }) });
  88  |     });
  89  |   });
  90  | 
  91  |   test("5-step onboarding wizard renders", async ({ page }) => {
  92  |     await page.goto(`${BASE}/onboarding`);
  93  |     await expect(page.locator("text=Upload your resume")).toBeVisible();
  94  |     await expect(page.locator("text=Step 1 of 5")).toBeVisible();
  95  |   });
  96  | 
  97  |   test("can navigate through onboarding steps", async ({ page }) => {
  98  |     await page.goto(`${BASE}/onboarding`);
  99  | 
  100 |     // Step 1: Skip resume
  101 |     await page.click('button:has-text("Skip for now")');
  102 |     await expect(page.locator("text=Your tech skills")).toBeVisible();
  103 |     await expect(page.locator("text=Step 2 of 5")).toBeVisible();
  104 | 
  105 |     // Step 2: Select skills
  106 |     await page.click("button:has-text('Python')");
  107 |     await page.click("button:has-text('React')");
  108 |     await page.click("button:has-text('Node.js')");
  109 |     await page.click('button:has-text("Continue")');
  110 |     await expect(page.locator("text=Where do you want to work")).toBeVisible();
  111 |   });
  112 | });
  113 | 
  114 | 
  115 | test.describe("Swipe Feed", () => {
  116 |   const mockJobs = [
  117 |     {
  118 |       id: "job-1",
  119 |       title: "Senior Python Developer",
  120 |       company: "Razorpay",
  121 |       company_logo: null,
  122 |       location: "Bangalore",
  123 |       is_remote: false,
  124 |       salary_min_lpa: 15,
  125 |       salary_max_lpa: 25,
  126 |       experience_min: 3,
  127 |       experience_max: 6,
  128 |       skills_required: ["Python", "FastAPI", "PostgreSQL"],
  129 |       description: "Build payment infrastructure.",
  130 |       apply_url: "https://razorpay.com/careers",
  131 |       job_type: "full-time",
  132 |       industry: "Engineering",
  133 |       source: "seed",
  134 |       posted_at: new Date().toISOString(),
```