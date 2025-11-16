import React, { useState, useEffect } from 'react';
import { Modal, Button, Form, Row, Col, Alert, Tabs, Tab, ListGroup, Image } from 'react-bootstrap';
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
          <h4>{details.tmdb_title} {(details.tmdb_id == 0 || details.tmdb_id === null) && <span className="badge bg-info ms-2">自定义</span>} <span className="text-muted">({details.tmdb_year})</span></h4>
          <p className="mb-1"><strong>类型:</strong> {details.tmdb_genres || '无'}</p>
          <p className="small mt-2" style={{maxHeight: '120px', overflowY: 'auto'}}>
            {details.tmdb_overview || '无可用概述。'}
          </p>
        </Col>
      </Row>
    </div>
  );
}

// New component to display the list of TMDb search results
function TMDbSearchResultsList({ results, onSelect }) {
  return (
    <ListGroup variant="flush" style={{maxHeight: '60vh', overflowY: 'auto'}}>
      {results.map(result => (
        <ListGroup.Item key={result.id} action>
          <Row className="align-items-center">
            <Col xs={3} md={2}>
              <Image 
                src={result.poster_path ? `https://image.tmdb.org/t/p/w92${result.poster_path}` : '/logo192.png'} 
                thumbnail 
                style={{width: '60px'}}
              />
            </Col>
            <Col xs={9} md={8}>
              <h6 className="mb-1">{result.title} <span className="text-muted">({result.year})</span></h6>
              <p className="small text-muted mb-1">{result.media_type === 'tv' ? '电视剧' : '电影'}</p>
              <p className="small" style={{maxHeight: '60px', overflowY: 'hidden', textOverflow: 'ellipsis'}}>
                {result.overview}
              </p>
            </Col>
            <Col md={2} className="d-none d-md-block text-end">
              <Button variant="outline-primary" size="sm" onClick={() => onSelect(result)}>选择</Button>
            </Col>
          </Row>
          <Row className="d-md-none mt-2">
             <Col>
                <Button variant="primary" size="sm" className="w-100" onClick={() => onSelect(result)}>选择</Button>
             </Col>
          </Row>
        </ListGroup.Item>
      ))}
    </ListGroup>
  );
}


function MediaModal({ media, tmdbSearchResults = [], onSave, onClose }) {
  const [formData, setFormData] = useState({});
  const [activeTab, setActiveTab] = useState('tmdb'); // 'tmdb' or 'manual'
  const [fetchError, setFetchError] = useState(null);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (tmdbSearchResults && tmdbSearchResults.length > 0) {
      setShowResults(true);
    } else {
      setShowResults(false);
    }

    if (media) {
      setFormData(media);
      if (media.tmdb_title && !media.tmdb_id) {
        setActiveTab('manual');
      } else {
        setActiveTab('tmdb');
      }
    } else {
      // Reset form for new entry
      setFormData({
        torname_regex: '',
        clean_title: '',
        cntitle: '',
        tmdb_id: '',
        tmdb_cat: 'movie',
        tmdb_title: '',
        tmdb_year: '',
        origin_country: '',
        tmdb_genres: '',
      });
      setActiveTab('tmdb');
    }
  }, [media, tmdbSearchResults]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    const dataToSave = { ...formData };

    // Ensure data types are correct before saving
    const year = parseInt(dataToSave.tmdb_year, 10);
    dataToSave.tmdb_year = isNaN(year) ? null : year;
    
    const tmdb_id = parseInt(dataToSave.tmdb_id, 10);
    dataToSave.tmdb_id = isNaN(tmdb_id) ? null : tmdb_id;

    // Convert empty string for regex to null to properly clear it
    if (dataToSave.torname_regex === '') {
      dataToSave.torname_regex = null;
    }

    if (activeTab === 'manual') {
      dataToSave.tmdb_id = null; 
    }
    
    onSave(dataToSave, activeTab);
  };

  const handleFetchTMDbDetails = (tmdbId, tmdbCat) => {
    const id = tmdbId || formData.tmdb_id;
    const cat = tmdbCat || formData.tmdb_cat;

    if (!id || !cat) {
      setFetchError('请输入 TMDb ID 并选择类别。');
      return;
    }
    setFetchError(null);
    axios.get(`/api/tmdb/details?tmdb_id=${id}&tmdb_cat=${cat}`)
      .then(response => {
        const data = response.data;
        setFormData(prev => ({
          ...prev,
          tmdb_id: data.id,
          tmdb_cat: data.media_type,
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

  const handleSelectTmdbResult = (result) => {
    // Populate form with selected result
    setFormData(prev => ({
      ...prev, // Keep existing fields like clean_title
      tmdb_id: result.id,
      tmdb_cat: result.media_type,
      tmdb_title: result.title,
      tmdb_year: result.year,
      tmdb_poster: result.poster_path,
      tmdb_overview: result.overview,
      // Fetch full details to get genres, etc.
    }));
    // Fetch more details in the background
    handleFetchTMDbDetails(result.id, result.media_type);
    // Hide the results list and show the form
    setShowResults(false);
    setActiveTab('tmdb');
  };

  const renderBody = () => {
    if (showResults) {
      return <TMDbSearchResultsList results={tmdbSearchResults} onSelect={handleSelectTmdbResult} />;
    }

    return (
      <Form>
        <Form.Group className="mb-3">
          <Form.Label>用于匹配的清理后标题</Form.Label>
          <Form.Control 
            type="text" 
            name="clean_title"
            value={formData.clean_title || ''} 
            onChange={handleChange} 
            placeholder='后端要求此项必填'
            required
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>中文标题</Form.Label>
          <Form.Control
            type="text"
            name="cntitle"
            value={formData.cntitle || ''}
            onChange={handleChange}
            placeholder='可选的中文标题'
          />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>种子全名匹配的正则规则</Form.Label>
          <Form.Control 
            type="text" 
            name="torname_regex" 
            value={formData.torname_regex || ''} 
            onChange={handleChange} 
            placeholder='例如: "My Movie .*\\(2023\\)"'
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
                  <Button variant="info" onClick={() => handleFetchTMDbDetails()} className="w-100">获取</Button>
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
    );
  }

  return (
    <Modal show onHide={onClose} size="lg">
      <Modal.Header closeButton>
        <Modal.Title>
          {showResults ? '选择一个TMDb匹配项' : (media ? '编辑媒体' : '添加新媒体')}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {renderBody()}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onClose}>取消</Button>
        {!showResults && <Button variant="primary" onClick={handleSave}>保存</Button>}
      </Modal.Footer>
    </Modal>
  );
}

export default MediaModal;
