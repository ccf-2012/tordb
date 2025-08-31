import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Alert, Tabs, Tab } from 'react-bootstrap';
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
  const [activeTab, setActiveTab] = useState('tmdb'); // 'tmdb' or 'manual'
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    if (media) {
      setFormData(media);
      if (media.tmdb_title && !media.tmdb_id) {
        setActiveTab('manual');
      } else {
        setActiveTab('tmdb');
      }
    } else {
      setFormData({
        torname_regex: '',
        clean_title: '',
        tmdb_id: '',
        tmdb_cat: 'movie',
        tmdb_title: '',
        tmdb_year: '',
        origin_country: '',
        tmdb_genres: '',
      });
      setActiveTab('tmdb');
    }
  }, [media]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    const dataToSave = { ...formData };

    // Ensure data types are correct before saving
    const year = parseInt(dataToSave.tmdb_year, 10);
    dataToSave.tmdb_year = isNaN(year) ? null : year;

    // Convert empty string for regex to null to properly clear it
    if (dataToSave.torname_regex === '') {
      dataToSave.torname_regex = null;
    }

    if (activeTab === 'manual') {
      dataToSave.tmdb_id = null; 
    }
    
    onSave(dataToSave, activeTab);
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
          tmdb_overview: data.overview,
          origin_country: Array.isArray(data.origin_country) ? data.origin_country.join(', ') : data.origin_country || ''
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
            <Form.Label>整理后标题</Form.Label>
            <Form.Control 
              type="text" 
              name="clean_title" 
              value={formData.clean_title || ''} 
              onChange={handleChange} 
              placeholder='后端要求此项必填'
              required
            />
          </Form.Group>

          <hr />

          <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)} id="media-entry-tabs" className="mb-3" fill>
            <Tab eventKey="tmdb" title="TMDb 查找">
              <div className="p-2">
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
                      <Form.Select name="tmdb_cat" value={formData.tmdb_cat || 'movie'} onChange={handleChange}>
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
              </div>
            </Tab>
            <Tab eventKey="manual" title="手动输入">
              <div className="p-2">
                <Form.Group className="mb-3">
                  <Form.Label>标题</Form.Label>
                  <Form.Control type="text" name="tmdb_title" value={formData.tmdb_title || ''} onChange={handleChange} />
                </Form.Group>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>年份</Form.Label>
                      <Form.Control type="number" name="tmdb_year" value={formData.tmdb_year || ''} onChange={handleChange} />
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>类别</Form.Label>
                      <Form.Select name="tmdb_cat" value={formData.tmdb_cat || 'movie'} onChange={handleChange}>
                        <option value="movie">电影</option>
                        <option value="tv">电视剧</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>
                <Form.Group className="mb-3">
                  <Form.Label>国家/地区</Form.Label>
                  <Form.Control type="text" name="origin_country" value={formData.origin_country || ''} onChange={handleChange} placeholder="例如: US, GB" />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>类型</Form.Label>
                  <Form.Control type="text" name="tmdb_genres" value={formData.tmdb_genres || ''} onChange={handleChange} placeholder="例如: Action, Science Fiction" />
                </Form.Group>
              </div>
            </Tab>
          </Tabs>
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
