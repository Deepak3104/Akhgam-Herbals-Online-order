USE akhgam_herbals;

START TRANSACTION;

-- Remove legacy/sample feedback entries.
DELETE FROM testimonials;

COMMIT;

SELECT COUNT(*) AS testimonials_remaining FROM testimonials;
SELECT COUNT(*) AS user_reviews_with_comment
FROM reviews
WHERE status = 'active' AND comment IS NOT NULL AND TRIM(comment) != '';
