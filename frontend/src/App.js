import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Button, Container, Row, Col, InputGroup, FormControl, Alert, Pagination, Modal } from 'react-bootstrap';
import { useTable, useExpanded } from 'react-table';
import MediaModal from './components/MediaModal';
import { useMediaQuery } from 'react-responsive';

// Configure axios to automatically add the API key to headers
axios.interceptors.request.use(config => {
  const apiKey = localStorage.getItem('tordb-api-key');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

const ITEMS_PER_PAGE = 10;

// The Table component now uses sorting
function Table({ columns, data, onEdit, onDelete }) {
  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
    visibleColumns,
  } = useTable(
    {
      columns,
      data,
    },
    useExpanded
  );

  return (
    <div className="table-responsive">
      <table {...getTableProps()} className="table table-sm table-hover" style={{ width: '100%' }}>
        <thead className="thead-dark">
          {headerGroups.map(headerGroup => {
            const { key, ...rest } = headerGroup.getHeaderGroupProps();
            return (
              <tr key={key} {...rest}>
                {headerGroup.headers.map(column => {
                  const { key, ...rest } = column.getHeaderProps({
                    style: { minWidth: column.minWidth, width: column.width, maxWidth: column.maxWidth, cursor: 'pointer' }
                  });
                  return (
                    <th key={key} {...rest}>
                      {column.render('Header')}
                    </th>
                  );
                })}
              </tr>
            )
          })}
        </thead>
        <tbody {...getTableBodyProps()}>
          {rows.map(row => {
            prepareRow(row);
            const { key, ...restRowProps } = row.getRowProps({ onClick: () => row.toggleRowExpanded(), style: { cursor: 'pointer' } });
            return (
              <React.Fragment key={key}>
                <tr {...restRowProps}>
                  {row.cells.map(cell => {
                    const { key, ...rest } = cell.getCellProps({style: {minWidth: cell.column.minWidth, width: cell.column.width, maxWidth: cell.column.maxWidth}});
                    return <td key={key} {...rest}>{cell.render('Cell')}</td>
                  })}
                </tr>
                {row.isExpanded ? (
                  <tr>
                    <td colSpan={visibleColumns.length} className="p-0">
                      <div className="p-3 bg-light">
                        <h6>种子列表 {row.original.tmdb_title} <span className="text-muted small">(分数: {row.original.id_score})</span></h6>
                        <ul className="list-group">
                          {row.original.torrents.map(t => (
                            <li key={t.id} className="list-group-item">
                              {t.infolink ? (
                                <a href={t.infolink} target="_blank" rel="noopener noreferrer">
                                  {t.name}
                                </a>
                              ) : (
                                t.name
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </td>
                  </tr>
                ) : null}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [mediaList, setMediaList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dbSearchQuery, setDbSearchQuery] = useState('');
  const [tmdbSearchQuery, setTmdbSearchQuery] = useState('');
  const [tmdbSearchResults, setTmdbSearchResults] = useState([]);

  // API Key State
  const [apiKey, setApiKey] = useState(localStorage.getItem('tordb-api-key') || '');
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [tempApiKey, setTempApiKey] = useState('');

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState(null);

  const isMobile = useMediaQuery({ query: '(max-width: 768px)' });

  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

  const handleAuthError = (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('tordb-api-key');
      setApiKey('');
      setError('API密钥无效或缺失，请重新输入。');
      setShowApiKeyModal(true);
    } else {
      setError(`发生错误: ${err.response?.data?.detail || err.message}`);
    }
    setLoading(false);
  };

  const fetchMedia = useCallback((page) => {
    if (!apiKey) {
      setShowApiKeyModal(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    const skip = (page - 1) * ITEMS_PER_PAGE;
    axios.get(`/api/tdb_media/?skip=${skip}&limit=${ITEMS_PER_PAGE}`)
      .then(response => {
        setMediaList(response.data.items || []);
        setTotalItems(response.data.total);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching media:', error);
        handleAuthError(error);
      });
  }, [apiKey]);

  useEffect(() => {
    if (!dbSearchQuery) {
      fetchMedia(currentPage);
    }
  }, [currentPage, dbSearchQuery, fetchMedia]);

  const handleDbSearch = () => {
    if (!apiKey) {
      setShowApiKeyModal(true);
      return;
    }
    setLoading(true);
    setError(null);
    if (!dbSearchQuery.trim()) {
      setCurrentPage(1);
      fetchMedia(1);
      return;
    }
    axios.get(`/api/tdb_media/search?q=${dbSearchQuery}`)
      .then(response => {
        setMediaList(response.data.items || []);
        setTotalItems(response.data.total);
        setCurrentPage(1); 
        setLoading(false);
      })
      .catch(handleAuthError);
  };

  const handleTmdbSearch = () => {
    if (!tmdbSearchQuery.trim()) {
      return;
    }
    setError(null);
    axios.get(`/api/tmdb/search?query=${encodeURIComponent(tmdbSearchQuery)}`)
      .then(response => {
        if (response.data && response.data.length > 0) {
          setTmdbSearchResults(response.data);
          handleOpenModal(); // Open modal without a selected media
        } else {
          setError('TMDb上没有找到匹配的结果。');
        }
        setTmdbSearchQuery('');
      })
      .catch(error => {
        handleAuthError(error);
      });
  };

  const handlePageChange = (pageNumber) => {
    if (pageNumber > 0 && pageNumber <= totalPages) {
      setCurrentPage(pageNumber);
    }
  };

  const handleOpenModal = (media = null) => {
    setSelectedMedia(media);
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedMedia(null);
    setTmdbSearchResults([]); // Clear results on close
  };

  const handleSaveMedia = (mediaData, mode) => {
    let request;
    if (mediaData.id && mediaData.id > 0) {
        request = axios.put(`/api/tdb_media/${mediaData.id}`, mediaData);
    } else {
        request = axios.post('/api/tdb_media/', mediaData);
    }

    request
      .then(() => {
        handleCloseModal();
        fetchMedia(currentPage);
      })
      .catch(handleAuthError);
  };

  const handleDeleteMedia = (mediaId) => {
    if (window.confirm('确定要删除这个媒体条目吗？')) {
      axios.delete(`/api/tdb_media/${mediaId}`)
        .then(() => fetchMedia(currentPage))
        .catch(handleAuthError);
    }
  };

  const handleSaveApiKey = () => {
    if (tempApiKey) {
      localStorage.setItem('tordb-api-key', tempApiKey);
      setApiKey(tempApiKey);
      setShowApiKeyModal(false);
      setCurrentPage(1); // Reset to page 1
      // The useEffect will trigger a fetch
    }
  };

  const columns = React.useMemo(
    () => {
      const baseColumns = [
        {
          Header: '海报',
          accessor: 'tmdb_poster',
          Cell: ({ value, row }) => {
            const tmdbUrl = `https://www.themoviedb.org/${row.original.tmdb_cat}/${row.original.tmdb_id}`;
            return (
              <div onClick={(e) => e.stopPropagation()}>
                { value ? 
                  <a href={tmdbUrl} target="_blank" rel="noopener noreferrer">
                    <img 
                      src={`https://image.tmdb.org/t/p/w92${value}`}
                      alt="poster" 
                      style={{ height: '120px', width: '80px', objectFit: 'cover', borderRadius: '5px' }} 
                    />
                  </a> : 
                  <div style={{ height: '120px', width: '80px', backgroundColor: '#e9ecef', borderRadius: '5px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span className="text-muted small">无海报</span>
                  </div>
                }
              </div>
            );
          },
          width: 92,
          minWidth: 92,
        },
        {
          Header: '媒体详情',
          accessor: 'tmdb_title',
          Cell: ({ row }) => (
            <div>
              <h6 className="mb-1">{row.original.tmdb_title} {row.original.tmdb_id < 0 && <span className="badge bg-success ms-2">自定义 {row.original.tmdb_id}</span>} <span className="text-muted font-weight-normal">({row.original.tmdb_year})</span></h6>
              <div className="small mb-1">
                <span className={`badge ${row.original.tmdb_cat === 'movie' ? 'tag-movie' : 'tag-tv'} me-1`}>
                  {row.original.tmdb_cat}
                </span>
                {row.original.tmdb_genres && <span className="text-muted">{row.original.tmdb_genres}</span>}
                {row.original.seasons && row.original.seasons.length > 0 && (
                  <span className="text-muted ms-2">
                    {row.original.seasons.map(season => `S${String(season.season_number).padStart(2, '0')}(共${season.episode_count}集)`).join(' ')}
                  </span>
                )}
                <span className="text-muted ms-2">{new Date(row.original.created_at).toLocaleString()}</span>
              </div>
              <p className="small" style={{ whiteSpace: 'pre-wrap', maxHeight: '70px', overflowY: 'auto' }}>
                {row.original.tmdb_overview}
              </p>
            </div>
          ),
          width: '60%',
        },
        {
          Header: '匹配标题',
          accessor: 'clean_title',
          Cell: ({ row }) => (
            <div>
              <div>{row.original.clean_title}</div>
              <div className="text-muted small">{row.original.tmdb_year}</div>
              {row.original.cntitle && <div className="text-muted small">{row.original.cntitle}</div>}
            </div>
          ),
          width: 220,
        },
      ];

      if (!isMobile) {
        baseColumns.push(
          {
            Header: '规则',
            accessor: 'torname_regex',
            Cell: ({ value }) => (
              value ? <code style={{ whiteSpace: 'normal' }}>{value}</code> : null
            ),
            width: 40,
          },
          {
            Header: '种子',
            accessor: 'torrents',
            Cell: ({ value }) => value.length,
            width: 30,

          },
          {
            Header: '操作',
            id: 'actions',
            Cell: ({ row }) => (
              <div className="text-center" onClick={(e) => e.stopPropagation()}>
                  <Button variant="outline-warning" size="sm" style={{ width: '35px' }} onClick={() => handleOpenModal(row.original)} title="编辑"><span role="img" aria-label="edit">&#9998;</span></Button>
                  <Button variant="outline-danger" size="sm" style={{ width: '35px' }} onClick={() => handleDeleteMedia(row.original.id)} title="删除"><span role="img" aria-label="delete">&#128465;</span></Button>
              </div>
            ),
            width: 30,
          }
        );
      }

      return baseColumns;
    },
    [isMobile, handleOpenModal, handleDeleteMedia]
  );

  return (
    <>
      <Modal show={showApiKeyModal} onHide={() => {}} backdrop="static" keyboard={false} centered>
        <Modal.Header>
          <Modal.Title>请输入 API 密钥</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <FormControl
            placeholder="API Key"
            aria-label="API Key"
            onChange={(e) => setTempApiKey(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSaveApiKey()}
          />
        </Modal.Body>
        <Modal.Footer>
          <Button variant="primary" onClick={handleSaveApiKey}>保存</Button>
        </Modal.Footer>
      </Modal>

      <div style={{ padding: '1rem', borderBottom: '1px solid #dee2e6', marginBottom: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{display: 'flex', alignItems: 'center'}}>
            <img src="/logo192.png" width="40" height="40" alt="logo" style={{ marginRight: '10px' }} />
            <h5 style={{ margin: 0 }}><a href="/" style={{ textDecoration: 'none', color: 'inherit' }}>TORDB: Taming the torrents</a></h5>
        </div>
        <Button variant="outline-secondary" size="sm" onClick={() => setShowApiKeyModal(true)}>更换密钥</Button>
      </div>

      <Container fluid style={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
        {error && <Alert variant="danger" onClose={() => setError(null)} dismissible>{error}</Alert>}
        <Row className="mb-3">
          <Col lg={4} md={6} xs={12} className="mb-2 mb-md-0">
            <InputGroup>
              <FormControl
                placeholder="搜索..."
                value={dbSearchQuery}
                onChange={e => setDbSearchQuery(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleDbSearch()}
              />
              <Button variant="info" onClick={handleDbSearch}>搜索</Button>
            </InputGroup>
          </Col>
          <Col lg={5} md={6} xs={12} className="mb-2 mb-md-0">
            <InputGroup>
              <FormControl
                placeholder="搜索TMDb，关键词/种子名/IMDb"
                value={tmdbSearchQuery}
                onChange={e => setTmdbSearchQuery(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleTmdbSearch()}
              />
              <Button variant="primary" onClick={handleTmdbSearch}>搜索TMDb</Button>
            </InputGroup>
          </Col>
          <Col lg={3} md={12} xs={12} className="text-lg-end">
              <Button variant="success" onClick={() => handleOpenModal()}>+ 手动添加</Button>
          </Col>
        </Row>

        {loading ? (
          <div>加载中...</div>
        ) : (
          <>
            <Table columns={columns} data={mediaList} onEdit={handleOpenModal} onDelete={handleDeleteMedia} />
            {totalPages > 0 && (
              <Row className="justify-content-center align-items-center mt-3">
                <Col xs="auto" className="text-muted small me-3 d-none d-md-block">
                  第 {currentPage} 页 / 共 {totalPages} 页 (总计: {totalItems})
                </Col>
                <Col xs="auto">
                  <Pagination size={isMobile ? 'sm' : undefined}>
                    <Pagination.First onClick={() => handlePageChange(1)} disabled={currentPage === 1} />
                    <Pagination.Prev onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1} />

                    {/* Render page numbers */}
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => {
                      if (page === 1 || page === totalPages || (page >= currentPage - 2 && page <= currentPage + 2)) {
                        return (
                          <Pagination.Item key={page} active={page === currentPage} onClick={() => handlePageChange(page)}>
                            {page}
                          </Pagination.Item>
                        );
                      } else if (page === currentPage - 3 || page === currentPage + 3) {
                        return <Pagination.Ellipsis key={page} />;
                      }
                      return null;
                    })}

                    <Pagination.Next onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages} />
                    <Pagination.Last onClick={() => handlePageChange(totalPages)} disabled={currentPage === totalPages} />
                  </Pagination>
                </Col>
              </Row>
            )}
          </>
        )}

        {showModal && (
          <MediaModal
            media={selectedMedia}
            tmdbSearchResults={tmdbSearchResults}
            onSave={handleSaveMedia}
            onClose={handleCloseModal}
          />
        )}
      </Container>
    </>
  );
}

export default App;
