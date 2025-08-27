import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Button, Container, Row, Col, InputGroup, FormControl, Alert, Pagination } from 'react-bootstrap';
// Import useSortBy
import { useTable, useExpanded } from 'react-table';
import MediaModal from './components/MediaModal';
import { useMediaQuery } from 'react-responsive';

const GROUPS_PER_PAGE = 10;

// Helper function to group media items by tmdb_id
const groupMediaByTmdbId = (mediaList) => {
  if (!mediaList) return [];
  const grouped = mediaList.reduce((acc, media) => {
    const key = media.tmdb_id;
    if (!acc[key]) {
      acc[key] = {
        ...media,
        originalItems: [media],
        torrents: [...media.torrents],
        torname_regex_list: [media.torname_regex],
      };
    } else {
      acc[key].originalItems.push(media);
      acc[key].torrents.push(...media.torrents);
      if (!acc[key].torname_regex_list.includes(media.torname_regex)) {
        acc[key].torname_regex_list.push(media.torname_regex);
      }
    }
    return acc;
  }, {});
  return Object.values(grouped);
};

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
          {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map(column => (
                // Add sorting props to the header
                <th {...column.getHeaderProps()} style={{ minWidth: column.minWidth, width: column.width, maxWidth: column.maxWidth, cursor: 'pointer' }}>
                  {column.render('Header')}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody {...getTableBodyProps()}>
          {rows.map(row => {
            prepareRow(row);
            return (
              <React.Fragment key={row.getRowProps().key}>
                <tr {...row.getRowProps({ onClick: () => row.toggleRowExpanded(), style: { cursor: 'pointer' } })}>
                  {row.cells.map(cell => (
                    <td {...cell.getCellProps({style: {minWidth: cell.column.minWidth, width: cell.column.width, maxWidth: cell.column.maxWidth}})}>{cell.render('Cell')}</td>
                  ))}
                </tr>
                {row.isExpanded ? (
                  <tr>
                    <td colSpan={visibleColumns.length} className="p-0">
                      <div className="p-3 bg-light">
                        <h7>种子列表 {row.original.tmdb_title} <span className="text-muted small">(分数: {row.original.id_score})</span></h7>
                        <ul className="list-group">
                          {row.original.torrents.map(t => 
                            <li key={t.id} className="list-group-item">{t.name}</li>
                          )}
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

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [totalGroups, setTotalGroups] = useState(0);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState(null);

  const isMobile = useMediaQuery({ query: '(max-width: 768px)' });

  const groupedMedia = useMemo(() => groupMediaByTmdbId(mediaList), [mediaList]);
  const totalPages = Math.ceil(totalGroups / GROUPS_PER_PAGE);

  const fetchMedia = (page) => {
    setLoading(true);
    const skip = (page - 1) * GROUPS_PER_PAGE;
    axios.get(`/api/media/?skip=${skip}&limit=${GROUPS_PER_PAGE}`)
      .then(response => {
        setMediaList(response.data.items);
        setTotalGroups(response.data.total);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching media:', error);
        setError('获取媒体数据失败。后端服务是否在运行？');
        setLoading(false);
      });
  };

  useEffect(() => {
    // Only fetch media if there is no active database search
    if (!dbSearchQuery) {
      fetchMedia(currentPage);
    }
  }, [currentPage, dbSearchQuery]);

  const handleDbSearch = () => {
    setLoading(true);
    setError(null);
    if (!dbSearchQuery.trim()) {
      // When search is cleared, fetch the first page of all media
      setCurrentPage(1);
      fetchMedia(1);
      return;
    }
    axios.get(`/api/media/search?q=${dbSearchQuery}`)
      .then(response => {
        setMediaList(response.data.items);
        setTotalGroups(response.data.total);
        // Reset to page 1 for search results
        setCurrentPage(1); 
        setLoading(false);
      })
      .catch(err => {
        setError(`搜索失败: ${err.response?.data?.detail || err.message}`);
        setLoading(false);
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
  };

  const handleSaveMedia = (mediaData, mode) => {
    let request;
    if (mediaData.id) { // Editing existing media
      request = axios.put(`/api/media/${mediaData.id}`, mediaData);
    } else { // Creating new media
        request = axios.post('/api/media/', mediaData);
    }

    request
      .then(() => {
        handleCloseModal();
        fetchMedia(currentPage);
      })
      .catch(err => {
        setError(`保存媒体失败: ${err.response?.data?.detail || err.message}`);
      });
  };

  const handleDeleteMedia = (mediaId) => {
    if (window.confirm('确定要删除这个媒体条目吗？')) {
      axios.delete(`/api/media/${mediaId}`)
        .then(() => fetchMedia(currentPage))
        .catch(err => {
          setError(`删除媒体失败: ${err.response?.data?.detail || err.message}`);
        });
    }
  };

  const columns = useMemo(
    () => {
      const baseColumns = [
        {
          Header: '海报',
          accessor: 'tmdb_poster',
          Cell: ({ value, row }) => (
            <div onClick={(e) => e.stopPropagation()}>
              { value ? 
                <img 
                  src={`https://image.tmdb.org/t/p/w92${value}`}
                  alt="poster" 
                  style={{ height: '120px', width: '80px', objectFit: 'cover', borderRadius: '5px' }} 
                /> : 
                <div style={{ height: '120px', width: '80px', backgroundColor: '#e9ecef', borderRadius: '5px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span className="text-muted small">无海报</span>
                </div>
              }
            </div>
          ),
          width: 92,
          minWidth: 92,
        },
        {
          Header: '媒体详情',
          accessor: 'tmdb_title',
          Cell: ({ row }) => (
            <div>
              <h6 className="mb-1">{row.original.tmdb_title} <span className="text-muted font-weight-normal">({row.original.tmdb_year})</span></h6>
              <div className="small mb-1">
                <span className={`badge ${row.original.tmdb_cat === 'movie' ? 'tag-movie' : 'tag-tv'} me-1`}>
                  {row.original.tmdb_cat}
                </span>
                {row.original.tmdb_genres && <span className="text-muted">{row.original.tmdb_genres}</span>}
              </div>
              <p className="small" style={{ whiteSpace: 'pre-wrap', maxHeight: '70px', overflowY: 'auto' }}>
                {row.original.tmdb_overview}
              </p>
            </div>
          ),
          width: '100%',
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
          width: 60,
        },
      ];

      if (!isMobile) {
        baseColumns.push(
          {
            Header: '规则',
            accessor: 'torname_regex_list',
            Cell: ({ value }) => (
              <ul className="list-unstyled mb-0 small">
                {value.map((regex, index) => (
                  <li key={index}><code style={{ whiteSpace: 'normal' }}>{regex}</code></li>
                ))}
              </ul>
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
                  <Button variant="outline-warning" size="sm" style={{ width: '45px' }} onClick={() => handleOpenModal(row.original.originalItems[0])} title="编辑"><span role="img" aria-label="edit">&#9998;</span></Button>
                  <Button variant="outline-danger" size="sm" style={{ width: '45px' }} onClick={() => handleDeleteMedia(row.original.originalItems[0].id)} title="删除"><span role="img" aria-label="delete">&#128465;</span></Button>
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
    <div style={{ padding: '1rem', borderBottom: '1px solid #dee2e6', marginBottom: '1rem', display: 'flex', alignItems: 'center' }}>
        <img src="/logo192.png" width="40" height="40" alt="logo" style={{ marginRight: '10px' }} />
        <h5 style={{ margin: 0 }}><a href="/" style={{ textDecoration: 'none', color: 'inherit' }}>TORDB: Taming the torrents</a></h5>
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
        <Col lg={3} md={12} xs={12} className="text-lg-end">
            <Button variant="success" onClick={() => handleOpenModal()}>+ 手动添加</Button>
        </Col>
      </Row>

      {loading ? (
        <div>加载中...</div>
      ) : (
        <>
          <Table columns={columns} data={groupedMedia} onEdit={handleOpenModal} onDelete={handleDeleteMedia} />
          {totalPages > 0 && (
            <Row className="justify-content-center align-items-center mt-3">
              <Col xs="auto" className="text-muted small me-3 d-none d-md-block">
                第 {currentPage} 页 / 共 {totalPages} 页 (总计: {totalGroups})
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
          onSave={handleSaveMedia}
          onClose={handleCloseModal}
        />
      )}
    </Container>
    </>
  );
}

export default App;
