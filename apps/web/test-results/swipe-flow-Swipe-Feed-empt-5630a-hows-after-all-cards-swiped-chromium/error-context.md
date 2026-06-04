# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: swipe-flow.spec.ts >> Swipe Feed >> empty state shows after all cards swiped
- Location: tests\e2e\swipe-flow.spec.ts:203:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Senior Python Developer')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Senior Python Developer')

```

```yaml
- img
- heading "SwipeHire" [level=1]
- paragraph: India's AI-powered job platform
- text: Mobile Number 🇮🇳 +91
- textbox "10-digit mobile number"
- button "Send OTP" [disabled]
- text: or
- button "Continue with Google":
  - img
  - text: Continue with Google
- paragraph: By continuing, you agree to SwipeHire's Terms & Privacy Policy
- alert
```

# Test source

```ts
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
  199 |     await page.click('button[aria-label="Apply"]');
  200 |     await expect(swipeRecorded).toBe(true);
  201 |   });
  202 | 
  203 |   test("empty state shows after all cards swiped", async ({ page }) => {
  204 |     await page.route("**/api/v1/swipes", async (route) => {
  205 |       await route.fulfill({ status: 201, body: JSON.stringify({ id: "sw-1", direction: "left", message: "Skipped" }) });
  206 |     });
  207 | 
  208 |     await page.goto(`${BASE}/swipe`);
> 209 |     await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });
      |                                                                ^ Error: expect(locator).toBeVisible() failed
  210 | 
  211 |     // Skip the card
  212 |     await page.click('button[aria-label="Skip"]');
  213 |     await expect(page.locator("text=You've seen all jobs!")).toBeVisible({ timeout: 3000 });
  214 |   });
  215 | });
  216 | 
  217 | 
  218 | test.describe("Applications Tracker", () => {
  219 |   test.beforeEach(async ({ page }) => {
  220 |     await page.route("**/api/v1/applications", async (route) => {
  221 |       await route.fulfill({
  222 |         status: 200,
  223 |         contentType: "application/json",
  224 |         body: JSON.stringify([
  225 |           {
  226 |             id: "app-1",
  227 |             job_id: "job-1",
  228 |             title: "Senior Python Developer",
  229 |             company: "Razorpay",
  230 |             company_logo: null,
  231 |             location: "Bangalore",
  232 |             status: "applied",
  233 |             applied_at: new Date().toISOString(),
  234 |             updated_at: new Date().toISOString(),
  235 |             auto_applied: false,
  236 |             notes: null,
  237 |             interview_date: null,
  238 |             offer_amount: null,
  239 |             match_score: 87,
  240 |           },
  241 |         ]),
  242 |       });
  243 |     });
  244 |   });
  245 | 
  246 |   test("application shows in Applied column", async ({ page }) => {
  247 |     await page.goto(`${BASE}/applications`);
  248 |     await expect(page.locator("text=Senior Python Developer")).toBeVisible({ timeout: 5000 });
  249 |     await expect(page.locator("text=Razorpay")).toBeVisible();
  250 |     await expect(page.locator("text=Applied")).toBeVisible();
  251 |   });
  252 | });
  253 | 
```