-- CHESS+ MySQL Schema
-- Contains tables for core application data, LSH signatures, and vector metadata

-- LSH Signatures Table
-- Stores MinHash signatures for locality-sensitive hashing
CREATE TABLE IF NOT EXISTS `lsh_signatures` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `signature_hash` VARCHAR(255) NOT NULL,
    `bucket_id` INT NOT NULL,
    `data_reference` VARCHAR(255) NOT NULL,
    `source_id` VARCHAR(255) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_signature_hash` (`signature_hash`),
    INDEX `idx_bucket_id` (`bucket_id`),
    INDEX `idx_data_reference` (`data_reference`),
    INDEX `idx_source_id` (`source_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Vector Metadata Table
-- Stores metadata about vectors stored in ChromaDB
CREATE TABLE IF NOT EXISTS `vector_metadata` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `chroma_id` VARCHAR(255) UNIQUE,
    `source_id` VARCHAR(255) NOT NULL,
    `text_chunk_id` VARCHAR(255),
    `metadata` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_source_id` (`source_id`),
    INDEX `idx_text_chunk_id` (`text_chunk_id`),
    INDEX `idx_chroma_id` (`chroma_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Additional application-specific tables would be defined here
-- This schema can be extended as needed for specific databases