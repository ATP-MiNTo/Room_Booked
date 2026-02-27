// src/components/FaceScanner.jsx
import React, { useRef, useState, useEffect, useCallback } from 'react';
import Webcam from 'react-webcam';
import * as faceapi from 'face-api.js';
import '../styles/FaceScanner.css'; 

const FaceScanner = ({ onScanComplete, onCancel }) => {
  const webcamRef = useRef(null);
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [status, setStatus] = useState('กำลังเตรียมระบบ...');
  const [capturedImage, setCapturedImage] = useState(null);

  const blinkDuration = useRef(0);
  const isProcessingRef = useRef(false); 

  useEffect(() => {
    const loadModels = async () => {
      const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';
      try {
        await Promise.all([
          faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
          faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
        ]);
        setModelsLoaded(true);
        setStatus('มองกล้อง แล้วกระพริบตา 1 ครั้ง');
      } catch (error) {
        console.error("Error:", error);
        setStatus('โหลดโมเดลไม่สำเร็จ');
      }
    };
    loadModels();
  }, []);

  const getDistance = (p1, p2) => Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2));
  const calculateEAR = (eye) => {
    const v1 = getDistance(eye[1], eye[5]);
    const v2 = getDistance(eye[2], eye[4]);
    const h = getDistance(eye[0], eye[3]);
    return (v1 + v2) / (2.0 * h);
  };

  const detectFace = useCallback(async () => {
    if (!modelsLoaded || isProcessingRef.current) return;

    try {
      if (webcamRef.current && webcamRef.current.video && webcamRef.current.video.readyState === 4) {
        const video = webcamRef.current.video;
        const videoWidth = video.videoWidth;
        const videoHeight = video.videoHeight;
        
        if (!videoWidth || !videoHeight) return;

        let detection;
        try {
            detection = await faceapi.detectSingleFace(
            video, 
            new faceapi.TinyFaceDetectorOptions({ inputSize: 224, scoreThreshold: 0.3 })
            ).withFaceLandmarks();
        } catch (aiError) {
            return; 
        }

        if (isProcessingRef.current) return;

        if (detection) {
          const box = detection.detection.box;
          const faceX = box.x + (box.width / 2);
          const faceY = box.y + (box.height / 2);
          const centerX = videoWidth / 2;
          const centerY = videoHeight / 2;
          const deviationX = Math.abs(faceX - centerX);
          const deviationY = Math.abs(faceY - centerY);

          if (deviationX > 60 || deviationY > 80) {
            setStatus('กรุณาขยับหน้ามาตรงกลาง');
            blinkDuration.current = 0; 
            return; 
          }

          if (box.width < 100) {
              setStatus('ขยับเข้ามาใกล้ๆ');
              blinkDuration.current = 0;
              return;
          }

          const landmarks = detection.landmarks;
          const leftEye = landmarks.getLeftEye();
          const rightEye = landmarks.getRightEye();
          const avgEAR = (calculateEAR(leftEye) + calculateEAR(rightEye)) / 2;

          if (avgEAR < 0.30) {
            blinkDuration.current += 1;
          } 
          else if (avgEAR > 0.30) {
            if (blinkDuration.current > 2) {
              setStatus('ยืนยันตัวตนสำเร็จ!');
              isProcessingRef.current = true; 
              capture(); 
              blinkDuration.current = 0;
            } else {
              blinkDuration.current = 0;
              if (!isProcessingRef.current) setStatus('กรุณากระพริบตา 1 ครั้ง');
            }
          }
        } else {
          setStatus('มองกล้อง...');
          blinkDuration.current = 0;
        }
      }
    } catch (error) {
      console.log("System message:", error.message);
    }
  }, [modelsLoaded]); 

  useEffect(() => {
    const interval = setInterval(() => detectFace(), 100);
    return () => clearInterval(interval);
  }, [detectFace]);

  const capture = () => {
    setTimeout(() => {
        if (webcamRef.current) {
          const imageSrc = webcamRef.current.getScreenshot();
          setCapturedImage(imageSrc);
          
          // สแกนเสร็จ โชว์รูปค้างไว้ 1.5 วิ แล้ววิ่งไปหน้าสรุปผลเลย (ไม่ต้องรอให้กดปุ่ม)
          setTimeout(() => {
            if (onScanComplete) onScanComplete(imageSrc);
          }, 1500);
        }
    }, 100);
  };

  return (
    // 👉 บังคับใส่ Inline Style เพื่อให้มันเป็น Popup ลอยทับหน้าจอ 100% 
    <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        zIndex: 99999, // ดันให้อยู่ชั้นบนสุด
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
    }}>
      <div className="scanner-container">
        <div className="scanner-wrapper" style={{ position: 'relative' }}>
          
          <Webcam
            ref={webcamRef}
            audio={false}
            playsInline={true}
            screenshotFormat="image/jpeg"
            screenshotQuality={0.8} // ความชัด 80% ไฟล์ไม่หนัก
            videoConstraints={{ width: 480, height: 640, facingMode: "user" }}
            className="webcam-video"
          />

          {!capturedImage && (
            <div className="face-overlay">
              <div className="face-cutout"></div>
            </div>
          )}

          {capturedImage && (
            <img 
              src={capturedImage} 
              alt="Captured" 
              className="captured-image" 
              style={{ zIndex: 10 }} 
            />
          )}
        </div>
        
        <div className="status-box">
          <h3 className={isProcessingRef.current ? "success-text" : ""}>{status}</h3>
          
          {/* 👉 ปุ่มลองใหม่หายไปแล้ว เหลือแค่ปุ่มยกเลิกตอนที่ยังสแกนไม่ผ่าน */}
          {!capturedImage && (
             <button onClick={onCancel} className="cancel-btn">ยกเลิก</button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FaceScanner;