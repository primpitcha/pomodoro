/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.7.2-MariaDB, for Win64 (AMD64)
--
-- Host: localhost    Database: pomodoro
-- ------------------------------------------------------
-- Server version	12.2.2-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `pomodoro_sessions`
--

DROP TABLE IF EXISTS `pomodoro_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pomodoro_sessions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `session_type` enum('work','short_break','long_break') NOT NULL,
  `duration_minutes` int(11) NOT NULL,
  `started_at` datetime NOT NULL,
  `ended_at` datetime DEFAULT NULL,
  `completed` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `2` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pomodoro_sessions`
--

LOCK TABLES `pomodoro_sessions` WRITE;
/*!40000 ALTER TABLE `pomodoro_sessions` DISABLE KEYS */;
INSERT INTO `pomodoro_sessions` VALUES
(1,NULL,1,'work',1,'2026-03-27 02:49:13','2026-03-27 02:49:20',0),
(2,NULL,1,'work',1,'2026-03-27 02:49:22','2026-03-27 02:49:24',0),
(3,NULL,1,'short_break',20,'2026-03-27 02:49:26','2026-03-27 02:49:28',0),
(4,NULL,1,'work',1,'2026-03-27 02:57:47','2026-03-27 02:57:48',0),
(5,NULL,1,'short_break',25,'2026-03-27 02:56:01','2026-03-27 03:01:05',1),
(6,NULL,1,'short_break',25,'2026-03-27 03:19:28','2026-03-27 03:24:32',1),
(7,NULL,9,'work',1,'2026-03-29 20:38:36','2026-03-29 20:38:38',0),
(8,NULL,9,'short_break',1,'2026-03-29 20:38:39','2026-03-29 20:38:42',0),
(9,NULL,9,'short_break',1,'2026-03-29 20:38:45','2026-03-29 20:38:49',0),
(10,NULL,9,'work',1,'2026-03-29 20:38:52','2026-03-29 20:39:00',0),
(11,NULL,9,'long_break',1,'2026-03-29 20:39:03','2026-03-29 20:39:25',0),
(12,NULL,9,'work',1,'2026-03-29 20:41:25','2026-03-29 20:41:31',0),
(13,NULL,9,'work',1,'2026-03-29 20:45:29','2026-03-29 20:45:39',0),
(14,NULL,9,'long_break',1,'2026-03-29 21:03:49','2026-03-29 21:03:53',0),
(15,NULL,9,'long_break',1,'2026-03-29 21:03:56','2026-03-29 21:03:59',0),
(16,NULL,31,'work',1,'2026-03-29 23:06:45','2026-03-29 23:06:51',0),
(17,NULL,31,'short_break',1,'2026-03-29 23:06:53','2026-03-29 23:06:57',0),
(18,NULL,36,'work',1,'2026-03-30 07:05:34','2026-03-30 07:05:36',0),
(19,NULL,36,'short_break',1,'2026-03-31 00:39:11','2026-03-31 00:39:14',0),
(20,NULL,36,'work',1,'2026-03-31 01:04:52','2026-03-31 01:04:55',0),
(21,NULL,36,'work',25,'2026-03-31 01:05:30','2026-03-31 01:30:40',1),
(22,92,36,'work',25,'2026-04-01 00:37:03','2026-04-01 01:02:07',1),
(23,94,36,'work',25,'2026-04-01 01:37:48','2026-04-01 02:03:08',1),
(24,92,36,'work',25,'2026-04-01 04:50:07','2026-04-01 05:15:11',1),
(25,99,5,'work',25,'2026-04-01 07:30:06','2026-04-01 07:56:08',1),
(26,93,36,'work',25,'2026-04-01 08:45:20','2026-04-01 09:10:38',1),
(27,100,36,'work',25,'2026-04-01 09:15:24','2026-04-01 09:40:30',1),
(28,103,40,'work',25,'2026-04-06 17:59:18','2026-04-06 18:24:21',1);
/*!40000 ALTER TABLE `pomodoro_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tasks`
--

DROP TABLE IF EXISTS `tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `title` varchar(255) NOT NULL,
  `note` text DEFAULT NULL,
  `status` text DEFAULT 'todo',
  `date` date DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=105 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tasks`
--

LOCK TABLES `tasks` WRITE;
/*!40000 ALTER TABLE `tasks` DISABLE KEYS */;
INSERT INTO `tasks` VALUES
(49,1,'ทดสอบ','โน้ต','todo','2026-03-26','2026-03-26 16:24:02',NULL),
(50,1,'อ่านหนังสือสอบอ.คิม','-ออกแบบux/uiด้วย','todo','2026-03-26','2026-03-26 16:26:02',NULL),
(53,1,'กราฟฟิก','ส่งวันนี้เที่ยงคืน!!!','todo','2026-03-27','2026-03-26 16:40:25',NULL),
(54,1,'ทดสอบจาก fastapi','โน้ตจาก fastapi','todo','2026-03-26','2026-03-26 16:40:41',NULL),
(55,1,'ทดสอบจาก fastapi','โน้ตจาก fastapi','todo','2026-03-26','2026-03-26 16:41:09',NULL),
(59,1,'อ่านหนังสือ','เตรียมสอบ','todo','2026-03-26','2026-03-26 16:53:33',NULL),
(60,5,'งานงาน','','todo','2026-03-27','2026-03-26 18:50:23',NULL),
(61,9,'การบ้านทำด่วน อังกฤษถ่ายคลิป','ส่งวันนี้เที่ยงคืน','todo','2026-03-29','2026-03-29 12:40:26',NULL),
(62,9,'tyjutku','-','todo','2026-03-29','2026-03-29 12:46:30',NULL),
(63,9,'string','string','string','2026-03-29','2026-03-29 12:49:06',NULL),
(65,9,'dgg','rgrh','todo','2026-03-29','2026-03-29 12:57:27',NULL),
(66,9,'ทำการบ้านด้วย','','todo','2026-03-29','2026-03-29 13:55:10',NULL),
(67,9,'งานเว้ยยยย','','todo','2026-03-29','2026-03-29 16:10:35',NULL),
(68,9,'งานนนนน','','todo','2026-03-30','2026-03-29 16:17:54',NULL),
(69,36,'งานนนนนน','','todo','2026-03-29','2026-03-29 16:27:34',NULL),
(70,36,'งานนนนน','','todo','2026-03-30','2026-03-29 16:29:58',NULL),
(71,9,'ycjyyjyj','','todo','2026-03-29','2026-03-29 16:41:39',NULL),
(72,9,'hnn','','todo','2026-03-29','2026-03-29 16:43:24',NULL),
(73,9,'ggghhr','','todo','2026-03-29','2026-03-29 16:54:04',NULL),
(74,36,'ttjyyj','jhhj','todo','2026-03-30','2026-03-29 23:20:22',NULL),
(75,36,'kjkjkj','hgkk','todo','2026-03-30','2026-03-29 23:20:27',NULL),
(76,36,'5254','','todo','2026-03-30','2026-03-30 00:19:43',NULL),
(77,36,'5254','','todo','2026-03-30','2026-03-30 00:19:44',NULL),
(78,36,'88','','todo','2026-03-30','2026-03-30 00:26:29',NULL),
(79,36,'14','','todo','2026-03-30','2026-03-30 00:26:36',NULL),
(80,36,'ฟ','ฟ','todo','2026-03-30','2026-03-30 16:23:34',NULL),
(81,36,'ฟ','ฟ','todo','2026-03-30','2026-03-30 16:23:35',NULL),
(84,36,'asdasd','asda','todo','2026-03-30','2026-03-30 16:51:12',NULL),
(85,36,'งานนนนนอังกิด','','todo','2026-03-30','2026-03-30 16:56:04',NULL),
(86,5,'งานนอาจารย์คิม','','todo','2026-03-31','2026-03-30 17:01:11',NULL),
(88,36,'ล้างจาน','[POMO:3] ในครัว','todo','2026-03-31','2026-03-30 18:37:55',NULL),
(89,36,'ปลูกผัก','[POMO:1] ในสวน','todo','2026-03-31','2026-03-30 18:38:14',NULL),
(90,36,'ตัดใจ','[POMO:1|0] ไม่ได้','todo','2026-03-31','2026-03-30 19:12:41',NULL),
(91,36,'อ่านหนังสือ','[POMO:1|0]','todo','2026-03-31','2026-03-30 19:13:02',NULL),
(92,36,'การบ้าน','[POMO:1|0]','todo','2026-04-01','2026-03-31 17:36:57',NULL),
(93,36,'ตัดหญ้า','[POMO:1|0] ตึกนัน','todo','2026-04-01','2026-03-31 18:24:14',NULL),
(94,36,'ไถนา','[POMO:1|0] ที่นาข้าว','todo','2026-04-01','2026-03-31 18:31:30',NULL),
(95,5,'Database','[POMO:1|0] ส่งวันศุกร์','todo','2026-04-01','2026-03-31 23:54:03',NULL),
(96,5,'Graphic Design','[POMO:2|0] ส่งวันเสาร์','todo','2026-04-01','2026-03-31 23:54:38',NULL),
(97,5,'Ux research','[POMO:4|0] ส่งวันจันทร์','todo','2026-04-01','2026-03-31 23:57:52',NULL),
(98,5,'UI','[POMO:1|0] ส่งวันศุกร์ 13','todo','2026-04-01','2026-04-01 00:27:12',NULL),
(99,5,'Marketing','[POMO:1|0] ส่งวันอังคาร','todo','2026-04-01','2026-04-01 00:29:57',NULL),
(100,36,'การบ้านอ.คิม','[POMO:1|0] ส่งวันนี้','todo','2026-04-01','2026-04-01 02:15:17',NULL),
(101,36,'การบ้านอ.คิม','[POMO:1|0] ส่งวันนี้','todo','2026-04-01','2026-04-01 02:15:17',NULL),
(102,36,'การบ้านวันนี้','[POMO:1|0]','todo','2026-04-01','2026-04-01 02:42:48',NULL),
(103,40,'การบ้านอ.คิม','[POMO:1|0] ส่งเที่ยงคืน','todo','2026-04-06','2026-04-06 10:59:07',NULL);
/*!40000 ALTER TABLE `tasks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_setting`
--

DROP TABLE IF EXISTS `user_setting`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_setting` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `work_minutes` int(11) DEFAULT 25,
  `short_break_minutes` int(11) DEFAULT 5,
  `long_break_minutes` int(11) DEFAULT 15,
  `rounds_before_long_break` int(11) DEFAULT 4,
  `selected_music_track` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_setting`
--

LOCK TABLES `user_setting` WRITE;
/*!40000 ALTER TABLE `user_setting` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_setting` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES
(1,'testuser','test@example.com','1234','2026-03-26 16:23:50'),
(2,'nungning','ning123@gmail.com','1234','2026-04-01 06:06:53'),
(5,'pom','prim@gmail.com','1234','2026-03-26 18:42:38'),
(6,'deebe','eegegeg','gergfwf','2026-03-26 20:41:40'),
(7,'deebe','gmktykt','ilui;f;','2026-03-26 20:42:58'),
(9,'posty','post@gmail.com','123','2026-03-29 12:16:31'),
(10,'Post','sbnd','enene','2026-03-29 14:58:51'),
(11,'Posbsn','ndmmdz','dndnmz','2026-03-29 15:43:33'),
(12,'Post','xnddm','dmmm','2026-03-29 15:44:07'),
(13,'Postbsns','sHnrdhrd','hdshrg','2026-03-29 15:45:17'),
(14,'zr,zj','fdnsrns','bsgeg','2026-03-29 15:45:39'),
(15,'zdmeM','neNrj','rhtjtrj','2026-03-29 15:46:17'),
(29,'ฟbhde','sgasg','gsgsgs','2026-03-29 16:05:17'),
(30,'cagsgs','fasgawg','gssgesg','2026-03-29 16:05:52'),
(31,'vbv','fff','fffff','2026-03-29 16:06:15'),
(32,'sgwg','gsgsg','hj,.','2026-03-29 16:07:56'),
(36,'primmy','111','1111','2026-03-29 16:19:20'),
(40,'prim','primmy@gmail.com','1234567','2026-04-06 10:58:44');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'pomodoro'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-04-06 18:40:19
