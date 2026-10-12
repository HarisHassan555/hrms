# Horilla HRMS — SaaS Product UI/UX Guidelines

## 1. Objective

This project is being transformed from an open-source HRMS interface into a polished, commercial-grade SaaS HR platform.

Every frontend change must follow a consistent design system.

The UI should feel:

- Modern
- Clean
- Professional
- Enterprise-ready
- Lightweight
- Spacious
- Consistent
- Accessible
- Responsive
- Suitable for HR, Payroll, Attendance, Recruitment, Performance, Assets, and Administration modules

Do not create isolated styles for individual pages.

Always reuse shared components, design tokens, spacing rules, typography, colors, and interaction patterns.

---

# 2. Design Direction

Use a modern enterprise SaaS visual language inspired by clean products such as:

- Linear
- Rippling
- Stripe Dashboard
- Vercel
- Modern HR platforms

Do not directly copy any specific product.

The final interface should have its own consistent identity.

Preferred visual direction:

- White cards
- Very light gray application background
- Indigo primary brand color
- Soft neutral borders
- Minimal shadows
- Rounded but not excessively rounded components
- Compact but readable tables
- Strong information hierarchy
- Limited use of bright colors
- Consistent iconography

Avoid making the interface look like a traditional Bootstrap admin template.

---

# 3. Global Color System

Use the following default design tokens.

```css
:root {
  /* Brand */
  --color-primary: #4F46E5;
  --color-primary-hover: #4338CA;
  --color-primary-active: #3730A3;
  --color-primary-soft: #EEF2FF;

  /* Application */
  --color-page-background: #F8FAFC;
  --color-surface: #FFFFFF;
  --color-surface-secondary: #F8FAFC;
  --color-surface-muted: #F1F5F9;

  /* Text */
  --color-text-primary: #0F172A;
  --color-text-secondary: #475569;
  --color-text-muted: #94A3B8;
  --color-text-disabled: #CBD5E1;

  /* Borders */
  --color-border: #E2E8F0;
  --color-border-light: #F1F5F9;
  --color-border-focus: #6366F1;

  /* Status */
  --color-success: #16A34A;
  --color-warning: #D97706;
  --color-danger: #DC2626;
  --color-info: #0284C7;
}
```

Do not introduce new brand colors unless required by a business requirement.

---

# 4. Semantic Status Colors

Status colors must communicate meaning.

## Success

Use for:

- Active
- Approved
- Completed
- Paid
- Present
- Successful

```text
Foreground: #15803D
Background: #DCFCE7
Border: #BBF7D0
```

## Warning

Use for:

- Pending
- In Review
- Late
- Awaiting Approval
- Expiring

```text
Foreground: #B45309
Background: #FEF3C7
Border: #FDE68A
```

## Danger

Use for:

- Rejected
- Failed
- Cancelled
- Critical
- Absent
- Overdue

```text
Foreground: #B91C1C
Background: #FEE2E2
Border: #FECACA
```

## Information

Use for:

- New
- Scheduled
- Informational
- Processing

```text
Foreground: #0369A1
Background: #E0F2FE
Border: #BAE6FD
```

## Neutral

Use for:

- Inactive
- Draft
- Unknown
- Disabled

```text
Foreground: #64748B
Background: #F1F5F9
Border: #E2E8F0
```

Do not use status colors decoratively.

---

# 5. Typography

Preferred font:

```text
Inter
```

Fallback:

```css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

Use the following typography scale.

```text
Page Title:
24px
Font Weight: 700
Line Height: 32px

Section Heading:
18px
Font Weight: 600

Card Heading:
14px
Font Weight: 600

Body:
14px
Font Weight: 400

Body Medium:
14px
Font Weight: 500

Label:
13px
Font Weight: 600

Small Text:
13px

Caption:
12px
```

Avoid excessive bold text.

Do not use more than 4-5 font sizes on the same page unless necessary.

---

# 6. Spacing System

Use a 4px-based spacing system.

Allowed preferred values:

```text
4px
8px
12px
16px
20px
24px
32px
40px
48px
64px
```

Common rules:

```text
Page horizontal padding:
24px to 32px

Card padding:
20px or 24px

Form field spacing:
16px

Grid gap:
16px or 20px

Major section spacing:
24px or 32px

Label to input:
6px to 8px
```

Do not use random spacing values unless layout requires them.

---

# 7. Border Radius

Use a consistent border-radius system.

```css
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
--radius-full: 999px;
```

Usage:

```text
Small controls:
6px

Inputs:
8px

Buttons:
8px

Dropdown items:
6px to 8px

Cards:
12px

Large containers:
12px to 16px

Modals:
16px

Badges:
999px
```

Do not make every component extremely rounded.

Avoid 20px+ radius on normal buttons, form fields, or tables.

---

# 8. Shadows

Keep shadows subtle.

Preferred shadows:

```css
--shadow-sm:
  0 1px 2px rgba(15, 23, 42, 0.05);

--shadow-md:
  0 6px 20px rgba(15, 23, 42, 0.08);

--shadow-lg:
  0 20px 40px rgba(15, 23, 42, 0.12);
```

Use:

```text
Cards:
none or shadow-sm

Dropdown:
shadow-md

Modal:
shadow-lg
```

Never use heavy black shadows.

---

# 9. Application Layout

The application should follow this general structure:

```text
Sidebar
Top Navigation
Page Header
Page Content
```

Recommended desktop dimensions:

```text
Sidebar:
248px to 264px

Topbar:
64px

Page padding:
24px to 32px
```

The application background should be:

```text
#F8FAFC
```

Content surfaces should normally be:

```text
#FFFFFF
```

---

# 10. Sidebar

Prefer a light sidebar.

```text
Background:
#FFFFFF

Border:
1px solid #E2E8F0
```

Recommended width:

```text
256px
```

Menu items:

```text
Height:
40px

Border Radius:
8px

Horizontal Padding:
12px
```

Default menu color:

```text
#475569
```

Active menu:

```text
Background:
#EEF2FF

Text:
#4338CA

Font Weight:
600
```

Icons:

```text
18px to 20px
```

Do not use large colorful icons for every menu item.

Nested menus must clearly show hierarchy.

---

# 11. Top Navigation

Top navigation should be simple and clean.

Recommended:

```text
Height:
64px

Background:
#FFFFFF

Bottom Border:
1px solid #E2E8F0
```

Typical content:

Left:

- Breadcrumb
- Page title where appropriate

Right:

- Search
- Notifications
- Help
- User avatar
- Profile dropdown

Avoid putting too many actions in the top navigation.

---

# 12. Page Header

Every major page should use a consistent page header.

Recommended structure:

```text
Title
Short description

Optional:
Breadcrumb

Right side:
Primary action
Secondary action
```

Example:

```text
Employees
Manage employees and their employment information.

[Export] [Add Employee]
```

Page title should not be inside a card unless required.

---

# 13. Cards

Default card:

```css
background: #FFFFFF;
border: 1px solid #E2E8F0;
border-radius: 12px;
padding: 20px;
```

Use very subtle or no shadow.

Do not use colored backgrounds for normal cards.

Cards should normally contain:

```text
Header
Optional description
Main content
Optional actions
```

Avoid nesting multiple cards unnecessarily.

---

# 14. KPI Cards

Dashboard KPI cards should be visually simple.

Preferred structure:

```text
Label
Main Value
Trend / Supporting Information
Optional Icon
```

Example:

```text
Total Employees

1,284

+6.2% from last month
```

Preferred value:

```text
26px to 32px
Font Weight: 700
```

Do not make complete cards green, blue, red, or orange.

If a color is needed, use it only for:

- Icon container
- Trend
- Small accent
- Status

---

# 15. Buttons

All buttons must use shared button styles.

## Primary Button

```css
height: 40px;
padding: 0 16px;
border-radius: 8px;
background: #4F46E5;
color: #FFFFFF;
font-size: 14px;
font-weight: 600;
border: 1px solid transparent;
```

Hover:

```text
#4338CA
```

Active:

```text
#3730A3
```

## Secondary Button

```text
Background:
#FFFFFF

Text:
#334155

Border:
#CBD5E1
```

Hover:

```text
#F8FAFC
```

## Ghost Button

Use for low-priority actions.

```text
Background:
Transparent

Text:
#475569
```

Hover:

```text
#F1F5F9
```

## Danger Button

Avoid full red buttons for normal list actions.

For normal delete actions:

```text
White background
Red text
Soft red border
```

Use a filled red button only inside destructive confirmation workflows.

---

# 16. Button Sizes

Use:

```text
Small:
32px

Default:
40px

Large:
44px
```

Default HRMS action buttons should normally be 40px high.

Icon buttons:

```text
36px or 40px square
```

---

# 17. Forms

Forms must feel clean, predictable, and easy to scan.

Default input:

```css
height: 42px;
padding: 0 12px;
border: 1px solid #CBD5E1;
border-radius: 8px;
background: #FFFFFF;
font-size: 14px;
color: #0F172A;
```

Input focus:

```css
border-color: #6366F1;
box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
outline: none;
```

Placeholder:

```text
#94A3B8
```

Disabled fields:

```text
Background:
#F8FAFC

Text:
#94A3B8
```

---

# 18. Form Labels

Labels:

```text
13px
Font Weight: 600
Color: #334155
```

Required fields:

```text
Employee Name *
```

Do not rely only on red color to indicate required fields.

---

# 19. Form Validation

Error input:

```text
Border:
#EF4444
```

Error message:

```text
12px
Color:
#DC2626
```

Example:

```text
Email Address *

[ invalid-email ]

Please enter a valid email address.
```

Success indicators should only be shown when useful.

---

# 20. Textarea

Recommended:

```text
Minimum Height:
100px to 120px

Padding:
12px

Border Radius:
8px
```

Allow vertical resizing where practical.

---

# 21. Select / Dropdown Controls

Select controls should visually match inputs.

Dropdown menu:

```css
background: #FFFFFF;
border: 1px solid #E2E8F0;
border-radius: 10px;
padding: 6px;
box-shadow: 0 10px 30px rgba(15, 23, 42, 0.10);
```

Dropdown option:

```text
Minimum Height:
36px to 38px

Border Radius:
6px
```

Hover:

```text
#F8FAFC
```

Selected:

```text
#EEF2FF
```

---

# 22. Checkboxes and Radio Buttons

Use the brand primary color for checked state.

Recommended control size:

```text
16px to 18px
```

Do not use oversized custom checkboxes.

Labels should remain readable and clickable.

---

# 23. Tables

Tables are a critical component of the HRMS.

Default table style:

```text
White background
No heavy outer border
Minimal horizontal separators
Soft table header
Comfortable row height
```

Header:

```text
Background:
#F8FAFC

Text:
#64748B

Font Size:
12px

Font Weight:
600
```

Rows:

```text
Minimum Height:
48px to 52px

Border Bottom:
1px solid #F1F5F9
```

Hover:

```text
#F8FAFC
```

Primary cell text:

```text
14px
#0F172A
```

Secondary information:

```text
12px to 13px
#64748B
```

Avoid vertical borders between every table cell.

---

# 24. Table Actions

Avoid showing 4-5 buttons inside every row.

For multiple actions use:

```text
⋯
```

or an equivalent three-dot action menu.

Examples:

```text
View
Edit
Deactivate
Delete
```

A single primary row action may be shown directly if important.

---

# 25. Table Toolbar

Tables that support filtering should have a consistent toolbar.

Example:

```text
[Search employees...]

[Department ▼]
[Status ▼]
[Location ▼]

                     [Export] [Add Employee]
```

Keep filters aligned and easy to clear.

---

# 26. Pagination

Use simple pagination.

Example:

```text
Showing 1–20 of 245

< Previous    1  2  3  ...  13    Next >
```

Do not use oversized pagination controls.

---

# 27. Status Badges

Use pill-shaped soft badges.

```css
padding: 4px 8px;
border-radius: 999px;
font-size: 12px;
font-weight: 600;
```

Do not use bright filled badges unless necessary.

---

# 28. Modals

Default modal sizes:

```text
Small:
420px

Default:
480px to 560px

Large Form:
640px to 720px
```

Modal:

```text
Background:
#FFFFFF

Border Radius:
16px

Shadow:
shadow-lg
```

Structure:

```text
Header
Title
Description

Body

Footer
```

Footer convention:

```text
Cancel
Primary Action
```

Destructive modal:

```text
Cancel
Delete
```

---

# 29. Drawers / Side Panels

Use drawers for:

- Employee quick view
- Filters
- Activity history
- Detail inspection
- Small editing workflows

Recommended desktop width:

```text
420px to 520px
```

Use a drawer instead of navigating away when context should remain visible.

---

# 30. Tabs

Tabs should be minimal.

Example:

```text
Profile
Job Information
Attendance
Leave
Payroll
Documents
Activity
```

Active tab:

```text
Text:
#4338CA

Bottom Border:
2px solid #4F46E5
```

Avoid pill tabs for every page.

---

# 31. Search

Search inputs should normally be:

```text
Height:
40px

Border Radius:
8px
```

Example placeholder:

```text
Search employees...
```

Use a search icon on the left.

Avoid adding a separate Search button unless required.

---

# 32. Filters

Filters must support clear states.

Recommended filter controls:

```text
Department
Branch
Employment Type
Status
Date Range
Manager
```

When filters are active, provide:

```text
Clear Filters
```

Avoid large dedicated filter pages for simple filtering.

---

# 33. Empty States

Never leave empty cards or tables looking broken.

Use:

```text
Simple icon
Clear title
One short explanation
Optional action
```

Example:

```text
No employees found

Try adjusting your search or filters.

[Clear Filters]
```

---

# 34. Loading States

Avoid showing blank pages during requests.

Preferred loading methods:

- Skeleton cards
- Skeleton table rows
- Small button spinner
- Inline loader

Avoid large full-page spinners unless the entire app is initializing.

---

# 35. Notifications / Toasts

Use toast notifications for short operation feedback.

Examples:

```text
Employee created successfully.
Leave request approved.
Payroll export failed.
```

Do not show blocking alerts for successful normal operations.

---

# 36. Icons

Use one icon library consistently.

Preferred:

- Lucide
- Heroicons
- Existing project icon library if already standardized

Recommended sizes:

```text
Navigation:
18px to 20px

Buttons:
16px to 18px

Cards:
18px to 22px
```

Do not mix multiple icon styles.

---

# 37. Dashboard Charts

Charts should follow the product palette.

Preferred palette:

```text
#4F46E5
#0EA5E9
#14B8A6
#22C55E
#F59E0B
#EF4444
#94A3B8
```

Guidelines:

- Use light grid lines
- Avoid 3D charts
- Avoid gradients unless subtle
- Avoid excessive labels
- Keep legends compact
- Always show units
- Tooltips should be readable
- Use bar and line charts where possible
- Pie/donut charts only for small category sets

Charts should answer a business question, not exist only for decoration.

---

# 38. Dashboard Structure

A dashboard should generally follow:

```text
Page Header

Global Filters

Primary KPI Cards

Main Trend Charts

Operational Insights

Actionable Tables

Recent Activity / Notifications
```

Avoid displaying too many KPIs at once.

Prioritize actionable information.

---

# 39. Responsive Design

All screens must work on:

```text
Desktop
Laptop
Tablet
Mobile
```

Breakpoints should follow the project's existing framework.

General behavior:

Desktop:

```text
Full sidebar
Multiple card columns
Full tables
```

Tablet:

```text
Collapsible sidebar
2-column cards
```

Mobile:

```text
Drawer navigation
Single-column cards
Responsive forms
Scrollable or transformed tables
```

Do not simply shrink desktop layouts.

---

# 40. Mobile Forms

On small screens:

```text
Inputs should normally use full width.
```

Two-column form fields should collapse to one column.

Primary action buttons may become full-width when appropriate.

---

# 41. Accessibility

All components must support accessibility.

Requirements:

- Maintain readable color contrast
- Provide visible keyboard focus
- Associate labels with inputs
- Provide button labels
- Avoid icon-only controls without accessible names
- Do not communicate state using color alone
- Support keyboard navigation
- Use semantic HTML where possible

---

# 42. HRMS-Specific UX Principles

HR systems contain large amounts of information.

Always prioritize:

```text
Clarity
Scanability
Fast filtering
Fast searching
Minimal clicks
Clear statuses
Strong date formatting
Consistent employee identification
```

Where employee information is displayed, prefer:

```text
Avatar
Employee Name
Employee Code
Designation
Department
```

depending on context.

---

# 43. Employee Display Pattern

Recommended employee identity component:

```text
[Avatar] Ali Raza
         EMP-1024
```

Secondary context may show:

```text
Senior Developer · IT
```

Do not repeatedly display all employee information in every table.

---

# 44. Date Formats

Use consistent date formatting throughout the product.

Preferred user-facing format:

```text
04 Oct 2026
```

Where time is needed:

```text
04 Oct 2026, 4:30 PM
```

Do not mix formats such as:

```text
04/10/26
2026-10-04
Oct 4th
```

on the same interface.

Backend/API formats may remain ISO.

---

# 45. Confirmation Rules

Ask for confirmation for destructive actions such as:

- Delete employee
- Remove role
- Cancel payroll
- Reject finalized workflow
- Remove company data

Do not show confirmation for harmless actions.

---

# 46. SaaS Settings Structure

Settings should be grouped.

Recommended categories:

```text
Organization

Employees

Attendance

Leave

Payroll

Recruitment

Performance

Notifications

Roles & Permissions

Integrations

Branding

Security

Billing
```

Do not show dozens of unrelated settings on one screen.

---

# 47. White-Label Support

Do not hard-code the Horilla brand directly into reusable UI components.

Brand-specific properties should eventually come from configuration.

Preferred configurable values:

```text
Company Name
Product Name
Logo
Favicon
Primary Brand Color
Login Illustration
Email Branding
Support Email
Support URL
Footer Text
```

Where possible, design components so the application can support multiple customer brands.

---

# 48. Theme Architecture

Do not scatter colors inside individual templates.

Bad:

```css
button {
    background: #4F46E5;
}
```

repeated across multiple files.

Preferred:

```css
button {
    background: var(--color-primary);
}
```

or use the project's centralized Tailwind / theme configuration.

Every reusable color must come from centralized tokens.

---

# 49. Component Reuse

Before creating a new component, check whether one already exists.

Prefer reusable components for:

- Button
- Input
- Select
- Textarea
- Checkbox
- Radio
- Badge
- Card
- Table
- Pagination
- Modal
- Drawer
- Tooltip
- Tabs
- Avatar
- Dropdown
- Search
- Date Picker
- Empty State
- Skeleton

Do not duplicate component markup across pages.

---

# 50. Do Not Change Business Logic During UI Work

When a task is specifically UI/UX related:

Do not change:

- API behavior
- Database schema
- Permissions
- Authentication
- Business calculations
- Existing workflow logic

unless explicitly required.

Visual refactoring must preserve functionality.

---

# 51. Existing Backend Compatibility

Horilla is an existing HRMS product.

Before changing templates or frontend behavior:

1. Inspect existing URL routes.
2. Inspect views/controllers.
3. Inspect form bindings.
4. Inspect JavaScript events.
5. Inspect permissions.
6. Inspect reusable partials.
7. Preserve existing field names and request payloads.

Do not break existing backend bindings simply to improve visual structure.

---

# 52. UI Refactoring Workflow

When redesigning an existing screen, follow this order:

1. Understand the current page purpose.
2. Identify existing functionality.
3. Identify actions available to the user.
4. Identify important business data.
5. Preserve all required functionality.
6. Apply the shared page layout.
7. Replace inconsistent controls with reusable components.
8. Improve hierarchy.
9. Improve spacing.
10. Improve table/form readability.
11. Add proper loading, empty, error, and success states.
12. Verify responsiveness.
13. Verify accessibility.
14. Verify existing functionality still works.

---

# 53. Do Not Overdesign

Do not use:

- Glassmorphism
- Excessive gradients
- Neon colors
- Heavy animation
- 3D effects
- Huge icons
- Decorative illustrations inside operational pages
- Excessive shadows
- Excessive rounded containers
- Multiple competing accent colors

This is an enterprise HR product.

Functionality and clarity come before decoration.

---

# 54. Animation

Animations must be subtle.

Recommended duration:

```text
150ms to 250ms
```

Use for:

- Hover
- Dropdown open
- Modal entry
- Drawer entry
- Small state transitions

Avoid long or distracting animations.

---

# 55. Hover States

Interactive components must have hover feedback.

Examples:

Buttons:

```text
Change background slightly
```

Cards:

```text
Only if clickable
```

Table row:

```text
#F8FAFC
```

Menu item:

```text
#F8FAFC
```

Do not make non-clickable cards animate on hover.

---

# 56. Focus States

Never remove focus outlines without replacement.

Preferred focus ring:

```css
box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15);
```

Keyboard users must be able to see the active control.

---

# 57. Form Page Layout

For long HR forms, avoid one huge vertical form.

Organize fields into logical sections.

Example:

```text
Personal Information

Employment Information

Contact Information

Bank Information

Emergency Contact

Documents
```

Use cards or section separators depending on page complexity.

---

# 58. Form Grid

Desktop:

```text
2-column layout
```

Use one column for:

- Long text
- Address
- Notes
- Rich content
- Fields requiring strong attention

Mobile:

```text
1 column
```

---

# 59. Detail Pages

Employee detail pages should not display all information in one large card.

Recommended structure:

```text
Employee Header

Summary

Tabs:
Overview
Attendance
Leave
Payroll
Documents
Performance
Assets
Activity
```

Use summary cards only for important metrics.

---

# 60. Login Page

The login page should feel like a commercial SaaS product.

Recommended structure:

Desktop:

```text
Brand / Visual Area
Login Form
```

or:

```text
Centered Login Card
```

Login card:

```text
Maximum Width:
400px to 440px
```

Use:

```text
Product logo
Welcome message
Email / username
Password
Remember me
Forgot password
Login button
```

Avoid overly large illustrations.

---

# 61. Navigation Naming

Menu labels should be simple and user-focused.

Prefer:

```text
Employees
Attendance
Leave
Payroll
Recruitment
Performance
Assets
Reports
Settings
```

Avoid technical/internal names in the primary UI.

---

# 62. Action Naming

Use clear verb-based actions.

Good:

```text
Add Employee
Approve Leave
Export Payroll
Create Job
Schedule Interview
Assign Asset
```

Avoid vague actions:

```text
Submit
Process
Execute
Go
```

when a clearer label is possible.

---

# 63. Data Density

HRMS users often work with large datasets.

Support information density without making the UI cramped.

Tables should remain relatively compact.

Forms should have comfortable spacing.

Dashboards should avoid excessive empty space.

Balance density depending on the workflow.

---

# 64. Multi-Tenant SaaS Readiness

When possible, avoid frontend assumptions tied to one company.

Do not hard-code:

- Company name
- Branch name
- Logo
- Country-specific strings
- Currency
- Date assumptions
- Employee numbering assumptions

Use configuration or backend data.

---

# 65. Dark Mode

Do not implement dark mode unless specifically requested.

The primary SaaS theme should be light.

Architecture should ideally use tokens so dark mode could be added later.

---

# 66. RTL / Localization Awareness

Avoid layouts that make future localization impossible.

Do not:

- Embed important text in images
- Hard-code widths around English labels
- Assume every label is short

Use flexible layout structures.

---

# 67. Error Pages

Use consistent pages for:

```text
403
404
500
Maintenance
```

They should include:

- Simple title
- Short explanation
- Safe navigation action

Do not expose stack traces to end users.

---

# 68. Permission-Based UI

Actions must respect existing user permissions.

If the backend already defines access rules, the UI must not expose inaccessible actions without reason.

Examples:

```text
Create
Edit
Delete
Approve
Export
```

Do not solve permission problems only by visually hiding controls if server-side authorization is required.

---

# 69. Tables With Large Datasets

For large datasets, prefer:

- Server-side pagination where supported
- Search
- Filters
- Sorting
- Page-size selector where useful

Do not render thousands of rows at once.

---

# 70. Required UI States

Every data-driven component should consider:

```text
Loading
Success
Empty
Error
Permission Denied
Disabled
```

Do not design only the successful state.

---

# 71. Visual Consistency Check

Before completing any UI task, verify:

```text
Is the page using the standard background?

Are cards using the standard radius?

Are inputs 42px high?

Are normal buttons 40px high?

Are colors coming from tokens?

Are table headers consistent?

Are badges using semantic colors?

Is typography consistent?

Is spacing based on the shared scale?

Are actions clear?

Is the design responsive?

Is existing functionality preserved?
```

---

# 72. Coding Rules for UI Changes

When modifying styles:

- Prefer existing frontend architecture.
- Prefer reusable classes/components.
- Avoid inline CSS unless the existing codebase strongly depends on it.
- Avoid `!important` unless absolutely required.
- Remove obsolete duplicated styles when safe.
- Do not introduce another CSS framework.
- Do not mix Bootstrap, Tailwind, and custom styles unnecessarily.
- Follow the project's established templating architecture.

---

# 73. Refactor Gradually

Horilla contains many screens.

Do not attempt to rewrite the entire frontend architecture in one change unless explicitly requested.

Preferred strategy:

```text
Step 1:
Global theme / tokens

Step 2:
Core layout

Step 3:
Shared components

Step 4:
Dashboard

Step 5:
Employee module

Step 6:
Attendance / Leave

Step 7:
Payroll

Step 8:
Recruitment / Performance

Step 9:
Remaining modules
```

Maintain application stability during redesign.

---

# 74. SaaS Quality Standard

Before considering a screen complete, it should look like it belongs to the same application as every other redesigned screen.

A user should not feel that:

```text
Dashboard belongs to one product
Employee page belongs to another
Payroll page belongs to another
Settings page belongs to another
```

Consistency is more important than making one page visually impressive.

---

# 75. Default Design Decision

When there is no explicit design requirement, use:

```text
Background:
#F8FAFC

Surface:
#FFFFFF

Primary:
#4F46E5

Text:
#0F172A

Border:
#E2E8F0

Card Radius:
12px

Input Radius:
8px

Button Radius:
8px

Modal Radius:
16px

Button Height:
40px

Input Height:
42px

Body Font:
14px

Page Padding:
24px

Card Padding:
20px
```

Use this as the safe default SaaS styling baseline.

---

# 76. Final Instruction to Codex

Whenever implementing or modifying Horilla HRMS UI:

1. First inspect the existing implementation.
2. Preserve existing functionality.
3. Identify reusable components.
4. Follow this design system.
5. Do not invent page-specific styling without reason.
6. Keep the interface minimal and enterprise-focused.
7. Optimize for real HR users performing daily operational work.
8. Maintain consistency across all modules.
9. Keep the code maintainable for future white-label customers.
10. Treat the application as a commercial SaaS product, not an admin template.