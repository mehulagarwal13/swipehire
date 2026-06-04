/**
 * E2E test — SwipeHire swipe flow
 * Tests: login → onboarding → swipe → applications tracker
 *
 * Run: npx playwright test
 * Prerequisites: web app running on localhost:3000, AI service on localhost:8000
 */
import { test, expect, type Page } from "@playwright/test";

const BASE = "http://127.0.0.1:3000";
const TEST_PHONE = "9999999999";
const TEST_OTP = "123456"; // dev mode returns this

async function loginWithOtp(page: Page) {
  await page.goto(`${BASE}/login`);

  // Enter phone number
  await page.fill('input[type="tel"]', TEST_PHONE);
  await page.click('button:has-text("Send OTP")');

  // Wait for OTP step
  await expect(page.locator('text=Enter OTP')).toBeVisible({ timeout: 5000 });

  // In dev mode the OTP is shown in a toast — intercept it
  // For test stability, mock the API call
  await page.fill('input[placeholder="6-digit OTP"]', TEST_OTP);
  await page.click('button:has-text("Verify & Sign In")');
}


test.describe("Authentication", () => {
  test("login page renders correctly", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    await expect(page.locator('h1:has-text("SwipeHire")')).toBeVisible();
    await expect(page.locator("text=India's AI job platform")).toBeVisible();
    await expect(page.locator('input[type="tel"]')).toBeVisible();
    await expect(page.locator('button:has-text("Send OTP")')).toBeVisible();
  });

  test("send OTP button disabled until 10 digits entered", async ({ page }) => {
    await page.goto(`${BASE}/login`);
    const btn = page.locator('button:has-text("Send OTP")');
    await expect(btn).toBeDisabled();

    await page.fill('input[type="tel"]', "12345");
    await expect(btn).toBeDisabled();

    await page.fill('input[type="tel"]', "9876543210");
    await expect(btn).not.toBeDisabled();
  });

  test("shows OTP input after phone submission", async ({ page }) => {
    await page.route("**/api/v1/auth/send-otp", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: "OTP sent", dev_otp: "123456" }),
      });
    });

    await page.goto(`${BASE}/login`);
    await page.fill('input[type="tel"]', "9876543210");
    await page.click('button:has-text("Send OTP")');

    await expect(page.locator('text=Enter OTP')).toBeVisible();
    await expect(page.locator('input[placeholder="6-digit OTP"]')).toBeVisible();
  });
});


test.describe("Onboarding", () => {
  test.beforeEach(async ({ page }) => {
    // Mock auth
    await page.route("**/api/v1/auth/verify-otp", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "mock_token",
          refresh_token: "mock_refresh",
          user_id: "user-123",
          is_onboarded: false,
        }),
      });
    });
    await page.route("**/api/v1/auth/send-otp", async (route) => {
      await route.fulfill({ status: 200, body: JSON.stringify({ message: "OTP sent", dev_otp: "123456" }) });
    });
  });

  test("5-step onboarding wizard renders", async ({ page }) => {
    await page.goto(`${BASE}/onboarding`);
    await expect(page.locator("text=Upload your resume")).toBeVisible();
    await expect(page.locator("text=Step 1 of 5")).toBeVisible();
  });

  test("can navigate through onboarding steps", async ({ page }) => {
    await page.goto(`${BASE}/onboarding`);

    // Step 1: Skip resume
    await page.click('button:has-text("Skip for now")');
    await expect(page.locator("text=Your tech skills")).toBeVisible();
    await expect(page.locator("text=Step 2 of 5")).toBeVisible();

    // Step 2: Select skills
    await page.click("button:has-text('Python')");
    await page.click("button:has-text('React')");
    await page.click("button:has-text('Node.js')");
    await page.click('button:has-text("Continue")');
    await expect(page.locator("text=Where do you want to work")).toBeVisible();
  });
});


test.describe("Swipe Feed", () => {
  const mockJobs = [
    {
      id: "job-1",
      title: "Senior Python Developer",
      company: "Razorpay",
      company_logo: null,
      location: "Bangalore",
      is_remote: false,
      salary_min_lpa: 15,
      salary_max_lpa: 25,
      experience_min: 3,
      experience_max: 6,
      skills_required: ["Python", "FastAPI", "PostgreSQL"],
      description: "Build payment infrastructure.",
      apply_url: "https://razorpay.com/careers",
      job_type: "full-time",
      industry: "Engineering",
      source: "seed",
      posted_at: new Date().toISOString(),
      match_score: 87,
      score_details: { skills: 90, experience: 100, location: 100, salary: 80, semantic: 75 },
      highlights: ["💰 ₹15–25 LPA", "📍 Bangalore", "🏢 3–6 years exp"],
    },
  ];

  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/jobs/feed**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockJobs),
      });
    });

    await page.route("**/api/v1/profile**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "user-123",
          full_name: "Test User",
          email: "test@example.com",
          phone: "9876543210",
          headline: "Python Developer",
          skills: ["Python", "React"],
          experience_years: 3,
          current_location: "Bangalore",
          preferred_locations: ["Bangalore"],
          min_salary_lpa: 10,
          max_salary_lpa: 20,
          job_types: ["full-time"],
          notice_period_days: 30,
          education: [],
          experience: [],
          projects: [],
          profile_score: 75,
          is_onboarded: true,
          resume_url: null,
        }),
      });
    });
  });

  test("job card renders with correct data", async ({ page }) => {
    await page.goto(`${BASE}/swipe`);
    await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Razorpay")).toBeVisible();
    await expect(page.locator("text=87%")).toBeVisible();
    await expect(page.locator("text=Python")).toBeVisible();
  });

  test("apply button triggers right-swipe API call", async ({ page }) => {
    let swipeRecorded = false;
    await page.route("**/api/v1/swipes", async (route) => {
      const body = JSON.parse(route.request().postData() || "{}");
      if (body.direction === "right") swipeRecorded = true;
      await route.fulfill({ status: 201, body: JSON.stringify({ id: "sw-1", direction: "right", application_id: "app-1", message: "Applied!" }) });
    });

    await page.goto(`${BASE}/swipe`);
    await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });

    // Click the Apply button
    await page.click('button[aria-label="Apply"]');
    await expect(swipeRecorded).toBe(true);
  });

  test("empty state shows after all cards swiped", async ({ page }) => {
    await page.route("**/api/v1/swipes", async (route) => {
      await route.fulfill({ status: 201, body: JSON.stringify({ id: "sw-1", direction: "left", message: "Skipped" }) });
    });

    await page.goto(`${BASE}/swipe`);
    await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });

    // Skip the card
    await page.click('button[aria-label="Skip"]');
    await expect(page.locator("text=You've seen all jobs!")).toBeVisible({ timeout: 3000 });
  });
});


test.describe("Applications Tracker", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/applications", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "app-1",
            job_id: "job-1",
            title: "Senior Python Developer",
            company: "Razorpay",
            company_logo: null,
            location: "Bangalore",
            status: "applied",
            applied_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            auto_applied: false,
            notes: null,
            interview_date: null,
            offer_amount: null,
            match_score: 87,
          },
        ]),
      });
    });
  });

  test("application shows in Applied column", async ({ page }) => {
    await page.goto(`${BASE}/applications`);
    await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Razorpay")).toBeVisible();
    await expect(page.locator("text=Applied")).toBeVisible();
  });
});
