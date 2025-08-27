import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Alert } from 'react-bootstrap';
import axios from 'axios';

// A dedicated component to display TMDb info in a clean, read-only format
function TMDbInfoBlock({ details }) {
  if (!details || !details.tmdb_title) {
    return (
        <div className="p-3 mb-3 bg-light rounded text-center text-muted">
            获取TMDb信息后将在此显示。
        </div>
    );
  }

  const posterUrl = details.tmdb_poster ? `https://image.tmdb.org/t/p/w154${details.tmdb_poster}` : null;

  return (
    <div className="p-3 mb-3 bg-light rounded">
      <Row>
        <Col md={3} className="text-center">
          {posterUrl ? (
            <img src={posterUrl} alt="poster" className="img-fluid rounded" />
          ) : (
            <div className="text-center text-muted pt-4">无海报</div>
          )}
        </Col>
        <Col md={9}>
          <h4>{details.tmdb_title} <span className="text-muted">({details.tmdb_year})</span></h4>
          <p className="mb-1"><strong>类型:</strong> {details.tmdb_genres || '无'}</p>
          <p className="small mt-2" style={{maxHeight: '120px', overflowY: 'auto'}}>
            {details.tmdb_overview || '无可用概述。'}
          </p>
        </Col>
      </Row>
    </div>
  );
}

function MediaModal({ media, onSave, onClose }) {
  const [formData, setFormData] = useState({});
  const [mode, setMode] = useState('tmdb');
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    if (media) {
      setFormData(media);
      setMode(media.tmdb_id ? 'tmdb' : 'manual');
    } else {
      setFormData({
        torname_regex: '',
        clean_title: '',
        tmdb_id: '',
        tmdb_cat: 'movie',
      });
      setMode('tmdb');
    }
  }, [media]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    onSave(formData, mode);
  };

  const handleFetchTMDbDetails = () => {
    if (!formData.tmdb_id || !formData.tmdb_cat) {
      setFetchError('请输入 TMDb ID 并选择类别。');
      return;
    }
    setFetchError(null);
    axios.get(`/api/tmdb/details?tmdb_id=${formData.tmdb_id}&tmdb_cat=${formData.tmdb_cat}`)
      .then(response => {
        const data = response.data;
        setFormData(prev => ({
          ...prev,
          tmdb_title: data.title || data.name,
          tmdb_poster: data.poster_path,
          tmdb_year: (data.release_date || data.first_air_date)?.substring(0, 4),
          tmdb_genres: data.genres?.map(g => g.name).join(', '),
          tmdb_overview: data.overview
        }));
      })
      .catch(error => {
        console.error('Error fetching TMDb details:', error);
        setFetchError(error.response?.data?.detail || '获取详情失败。');
      });
  };

  return (
    <Modal show onHide={onClose} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>{media ? '编辑媒体' : '添加新媒体'}</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Form>
          {/* Always show the regex field at the top */}
          <Form.Group className="mb-3">
            <Form.Label>种子名称匹配规则</Form.Label>
            <Form.Control 
              type="text" 
              name="torname_regex" 
              value={formData.torname_regex || ''} 
              onChange={handleChange} 
              placeholder='例如: "My Movie Title 2023"'
            />
          </Form.Group>

          <Form.Group className="mb-3">
            <Form.Label>标题</Form.Label>
            <Form.Control 
              type="text" 
              name="clean_title" 
              value={formData.clean_title || ''} 
              onChange={handleChange} 
              placeholder='例如: "My Movie Title"'
            />
          </Form.Group>

          {/* TMDb Details Section */}
          <h5 className="mt-4">TMDb 匹配</h5>
          <hr />
          <Row className="align-items-end">
            <Col md={5}>
              <Form.Group>
                <Form.Label>TMDb ID</Form.Label>
                <Form.Control type="number" name="tmdb_id" value={formData.tmdb_id || ''} onChange={handleChange} placeholder="例如: 603" />
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group>
                <Form.Label>类别</Form.Label>
                <Form.Select name="tmdb_cat" value={formData.tmdb_cat || ''} onChange={handleChange}>
                  <option value="movie">电影</option>
                  <option value="tv">电视剧</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={3}>
              <Button variant="info" onClick={handleFetchTMDbDetails} className="w-100">获取</Button>
            </Col>
          </Row>
          {fetchError && <Alert variant="danger" className="mt-3">{fetchError}</Alert>}
          
          <div className="mt-3">
            <TMDbInfoBlock details={formData} />
          </div>

        </Form>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>取消</Button>
        <Button variant="primary" onClick={handleSave}>保存</Button>
      </Modal.Footer>
    </Modal>
  );
}

export default MediaModal;