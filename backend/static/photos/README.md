# Employee Photos Directory

This directory stores employee profile photos for the CID system.

## File Naming Convention
- Files should be named using a sanitized version of the email or a unique identifier
- Supported formats: .jpg, .jpeg, .png, .gif, .webp
- Example: `john_doe.jpg` or `john.doe@example.com.png`

## Maximum File Size
- Recommended: 500KB or less
- Maximum: 2MB

## Image Dimensions
- Recommended: 200x200 pixels (square)
- Will be displayed as 40x40 pixels in the sidebar

## Database Reference
Photos are referenced in the `cids.photo_emp` table:
- email: Employee email
- photo_path: Relative path to the photo file (e.g., "john_doe.jpg")

## Default Avatar
If no photo exists for an employee, a default avatar will be displayed.