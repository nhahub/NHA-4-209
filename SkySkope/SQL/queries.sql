-- ═══════════════════════════════════════════════════════════
-- Sky Scope Analytics — SQL Analysis Queries
-- Dataset: US Domestic flights (Jan–Jul 2022)
-- ═══════════════════════════════════════════════════════════


-- ─────────────────────────────────────────
-- 1. Total number of flights in the dataset
-- ─────────────────────────────────────────
SELECT COUNT(*) AS Total_flights
FROM flights;


-- ─────────────────────────────────────────
-- 2. Total number of distinct airlines
-- ─────────────────────────────────────────
SELECT COUNT(DISTINCT Airline) AS Total_Airlines
FROM flights;


-- ─────────────────────────────────────────
-- 3. Airline with the highest number of flights
-- ─────────────────────────────────────────
SELECT Airline, COUNT(*) AS Total_flights
FROM flights
GROUP BY Airline
ORDER BY Total_flights DESC
LIMIT 1;


-- ─────────────────────────────────────────
-- 4. Average departure delay (completed flights only, excludes -1 sentinel values)
-- ─────────────────────────────────────────
SELECT AVG(DepDelayMinutes) AS Avg_Dep_Delay
FROM flights
WHERE DepDelayMinutes >= 0;


-- ─────────────────────────────────────────
-- 5. Maximum recorded departure delay
-- ─────────────────────────────────────────
SELECT MAX(DepDelayMinutes) AS Max_Dep_Delay
FROM flights
WHERE DepDelayMinutes >= 0;


-- ─────────────────────────────────────────
-- 6. Shortest flight distance
-- ─────────────────────────────────────────
SELECT MIN(Distance) AS Min_Distance
FROM flights
;

-- ─────────────────────────────────────────
-- 7. Longest flight distance
-- ─────────────────────────────────────────
SELECT MAX(Distance) AS Max_Distance
FROM flights


-- ─────────────────────────────────────────
-- 8. Average flight distance
-- ─────────────────────────────────────────
SELECT AVG(Distance) AS Avg_Distance
FROM flights


-- ─────────────────────────────────────────
-- 9. Number of delayed flights (departure delay > 0, completed flights only)
-- ─────────────────────────────────────────
SELECT COUNT(*) AS Delayed_flights
FROM flights
WHERE DepDelayMinutes > 0


-- ─────────────────────────────────────────
-- 10. Number of on-time flights (no departure delay, completed flights only)
-- ─────────────────────────────────────────
SELECT COUNT(*) AS On_Time_flights
FROM flights
WHERE DepDelayMinutes = 0


-- ─────────────────────────────────────────
-- 11. Busiest departure airport
-- Includes Diverted flights since the aircraft physically departed
-- ─────────────────────────────────────────
SELECT Origin, COUNT(*) AS Total_flights
FROM flights
WHERE flightstatus IN ('Completed', 'Diverted')
GROUP BY Origin
ORDER BY Total_flights DESC
LIMIT 1;

-- ─────────────────────────────────────────
-- 12. Busiest arrival airport
-- Completed flights only — Diverted flights did not reach their original destination
-- ─────────────────────────────────────────
SELECT Dest, COUNT(*) AS Total_flights
FROM flights
WHERE flightstatus = 'Completed'
GROUP BY Dest
ORDER BY Total_flights DESC
LIMIT 1;


-- ─────────────────────────────────────────
-- 13. Total flights per airline
-- ─────────────────────────────────────────
SELECT Airline, COUNT(*) AS Total_flights
FROM flights
GROUP BY Airline
ORDER BY Total_flights DESC


-- ─────────────────────────────────────────
-- 14. Average air time per airline (completed flights only, excludes -1 sentinel values)
-- ─────────────────────────────────────────
SELECT Airline, AVG(AirTime) AS Avg_Air_Time
FROM flights
WHERE AirTime >= 0
GROUP BY Airline
ORDER BY Avg_Air_Time DESC


-- ─────────────────────────────────────────
-- 15. Total departures per airport
-- Includes Diverted flights since the aircraft physically departed
-- ─────────────────────────────────────────
SELECT Origin, COUNT(*) AS Total_flights
FROM flights
WHERE flightstatus IN ('Completed', 'Diverted')
GROUP BY Origin
ORDER BY Total_flights DESC


-- ─────────────────────────────────────────
-- 16. Total arrivals per airport
-- Completed flights only — Diverted flights did not reach their original destination
-- ─────────────────────────────────────────
SELECT Dest, COUNT(*) AS Total_flights
FROM flights
WHERE flightstatus = 'Completed'
GROUP BY Dest
ORDER BY Total_flights DESC


-- ─────────────────────────────────────────
-- 17. Average departure delay per airline (excludes -1 sentinel values)
-- ─────────────────────────────────────────
SELECT Airline, AVG(DepDelayMinutes) AS Avg_Delay
FROM flights
WHERE DepDelayMinutes >= 0
GROUP BY Airline
ORDER BY Avg_Delay DESC


-- ─────────────────────────────────────────
-- 18. Number of long-haul flights (distance > 1000 miles)
-- ─────────────────────────────────────────
SELECT COUNT(*) AS Long_flights
FROM flights
WHERE Distance > 1000


-- ─────────────────────────────────────────
-- 19. Average actual elapsed flight time (excludes -1 sentinel values)
-- ─────────────────────────────────────────
SELECT AVG(ActualElapsedTime) AS Avg_Actual_Time
FROM flights
WHERE ActualElapsedTime >= 0


-- ─────────────────────────────────────────
-- 20. Total flights per month
-- Note: dataset covers Jan–Jul 2022 only
-- ─────────────────────────────────────────
SELECT Flight_Month, MonthName, COUNT(*) AS Total_flights
FROM flights
GROUP BY Flight_Month, MonthName
ORDER BY Flight_Month


-- ═══════════════════════════════════════════════════════════
-- ADVANCED QUERIES
-- ═══════════════════════════════════════════════════════════


-- ─────────────────────────────────────────
-- 21. Airline on-time performance ranking using RANK()
-- ─────────────────────────────────────────
SELECT
    Airline,
    COUNT(*) AS Total_flights,
    SUM(CASE WHEN IsDelayed = 0 THEN 1 ELSE 0 END) AS OnTime_flights,
    ROUND(SUM(CASE WHEN IsDelayed = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS OnTime_Rate,
    RANK() OVER (
        ORDER BY SUM(CASE WHEN IsDelayed = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) DESC
    ) AS Performance_Rank
FROM flights
WHERE flightstatus = 'Completed'
GROUP BY Airline
ORDER BY Performance_Rank


-- ─────────────────────────────────────────
-- 22. Top 10 worst routes by average arrival delay
-- Filtered to routes with more than 1000 flights for statistical significance
-- ─────────────────────────────────────────
SELECT
    CONCAT(Origin, ' → ', Dest) AS RouteKey,
    COUNT(*) AS Total_flights,
    ROUND(AVG(ArrDelay), 2) AS Avg_Arr_Delay,
    ROUND(AVG(DepDelay), 2) AS Avg_Dep_Delay,
    SUM(CASE WHEN IsDelayed = 1 THEN 1 ELSE 0 END) AS Delayed_flights,
    ROUND(SUM(CASE WHEN IsDelayed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS Delay_Rate
FROM flights
WHERE flightstatus = 'Completed'
GROUP BY Origin, Dest
HAVING COUNT(*) > 1000
ORDER BY Avg_Arr_Delay DESC
LIMIT 10;

-- ─────────────────────────────────────────
-- 23. Weekday vs Weekend flight performance comparison
-- ─────────────────────────────────────────
SELECT
    CASE WHEN Is_Weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS Day_Type,
    COUNT(*) AS Total_flights,
    ROUND(AVG(ArrDelay), 2) AS Avg_Arr_Delay,
    ROUND(SUM(CASE WHEN IsDelayed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS Delay_Rate,
    ROUND(SUM(CASE WHEN flightstatus = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS Cancel_Rate
FROM flights
GROUP BY Is_Weekend
ORDER BY Day_Type


-- ─────────────────────────────────────────
-- 24. Delay category breakdown per airline using CTE
-- ─────────────────────────────────────────
WITH DelayCategorized AS (
    SELECT
        Airline,
        DelayCategory,
        COUNT(*) AS Flight_Count
    FROM flights
    GROUP BY Airline, DelayCategory
),
AirlineTotals AS (
    SELECT
        Airline,
        SUM(Flight_Count) AS Total
    FROM DelayCategorized
    GROUP BY Airline
)
SELECT
    d.Airline,
    d.DelayCategory,
    d.Flight_Count,
    ROUND(d.Flight_Count * 100.0 / t.Total, 2) AS Percentage
FROM DelayCategorized d
JOIN AirlineTotals t ON d.Airline = t.Airline
ORDER BY d.Airline, d.DelayCategory


-- ─────────────────────────────────────────
-- 25. Monthly cumulative flight count with running total and delay rate
-- ─────────────────────────────────────────
SELECT
    Flight_Month,
    MonthName,
    COUNT(*) AS Monthly_flights,
    SUM(COUNT(*)) OVER (ORDER BY Flight_Month) AS Running_Total,
    ROUND(SUM(CASE WHEN IsDelayed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS Monthly_Delay_Rate
FROM flights
WHERE flightstatus = 'Completed'
GROUP BY Flight_Month, MonthName
ORDER BY Flight_Month
