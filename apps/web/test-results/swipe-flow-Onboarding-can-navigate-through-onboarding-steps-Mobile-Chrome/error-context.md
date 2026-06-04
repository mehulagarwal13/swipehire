# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: swipe-flow.spec.ts >> Onboarding >> can navigate through onboarding steps
- Location: tests\e2e\swipe-flow.spec.ts:97:7

# Error details

```
Error: page.goto: Page crashed
Call log:
  - navigating to "http://127.0.0.1:3000/onboarding", waiting until "load"

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
  34  |     await expect(page.locator("text=SwipeHire")).toBeVisible();
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
> 98  |     await page.goto(`${BASE}/onboarding`);
      |                ^ Error: page.goto: Page crashed
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
  135 |       match_score: 87,
  136 |       score_details: { skills: 90, experience: 100, location: 100, salary: 80, semantic: 75 },
  137 |       highlights: ["💰 ₹15–25 LPA", "📍 Bangalore", "🏢 3–6 years exp"],
  138 |     },
  139 |   ];
  140 | 
  141 |   test.beforeEach(async ({ page }) => {
  142 |     await page.route("**/api/v1/jobs/feed**", async (route) => {
  143 |       await route.fulfill({
  144 |         status: 200,
  145 |         contentType: "application/json",
  146 |         body: JSON.stringify(mockJobs),
  147 |       });
  148 |     });
  149 | 
  150 |     await page.route("**/api/v1/profile**", async (route) => {
  151 |       await route.fulfill({
  152 |         status: 200,
  153 |         contentType: "application/json",
  154 |         body: JSON.stringify({
  155 |           user_id: "user-123",
  156 |           full_name: "Test User",
  157 |           email: "test@example.com",
  158 |           phone: "9876543210",
  159 |           headline: "Python Developer",
  160 |           skills: ["Python", "React"],
  161 |           experience_years: 3,
  162 |           current_location: "Bangalore",
  163 |           preferred_locations: ["Bangalore"],
  164 |           min_salary_lpa: 10,
  165 |           max_salary_lpa: 20,
  166 |           job_types: ["full-time"],
  167 |           notice_period_days: 30,
  168 |           education: [],
  169 |           experience: [],
  170 |           projects: [],
  171 |           profile_score: 75,
  172 |           is_onboarded: true,
  173 |           resume_url: null,
  174 |         }),
  175 |       });
  176 |     });
  177 |   });
  178 | 
  179 |   test("job card renders with correct data", async ({ page }) => {
  180 |     await page.goto(`${BASE}/swipe`);
  181 |     await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });
  182 |     await expect(page.locator("text=Razorpay")).toBeVisible();
  183 |     await expect(page.locator("text=87%")).toBeVisible();
  184 |     await expect(page.locator("text=Python")).toBeVisible();
  185 |   });
  186 | 
  187 |   test("apply button triggers right-swipe API call", async ({ page }) => {
  188 |     let swipeRecorded = false;
  189 |     await page.route("**/api/v1/swipes", async (route) => {
  190 |       const body = JSON.parse(route.request().postData() || "{}");
  191 |       if (body.direction === "right") swipeRecorded = true;
  192 |       await route.fulfill({ status: 201, body: JSON.stringify({ id: "sw-1", direction: "right", application_id: "app-1", message: "Applied!" }) });
  193 |     });
  194 | 
  195 |     await page.goto(`${BASE}/swipe`);
  196 |     await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });
  197 | 
  198 |     // Click the Apply button
```