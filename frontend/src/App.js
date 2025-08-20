import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Button, Container, Row, Col, InputGroup, FormControl, Alert, Pagination } from 'react-bootstrap';
// Import useSortBy
import { useTable, useSortBy, useExpanded } from 'react-table';
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
      // Set initial sort state
      initialState: { sortBy: [{ id: 'tmdb_year', desc: true }] },
    },
    useSortBy, // Use sorting
    useExpanded
  );

  return (
    <div className="table-responsive">
      <table {...getTableProps()} className="table table-sm table-hover" style={{  width: '100%' }}>
        <thead className="thead-dark">
          {headerGroups.map(headerGroup => (
            <tr {...headerGroup.getHeaderGroupProps()}>
              {headerGroup.headers.map(column => (
                // Add sorting props to the header
                <th {...column.getHeaderProps(column.getSortByToggleProps())} style={{ width: column.width, cursor: 'pointer' }}>
                  {column.render('Header')}
                  {/* Add a sort direction indicator */}
                  <span>
                    {column.isSorted
                      ? column.isSortedDesc
                        ? ' 🔽'
                        : ' 🔼'
                      : ''}
                  </span>
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
                    <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
                  ))}
                </tr>
                {row.isExpanded ? (
                  <tr>
                    <td colSpan={visibleColumns.length} className="p-0">
                      <div className="p-3 bg-light">
                        <h5>Torrents for {row.original.tmdb_title}</h5>
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
  const [searchQuery, setSearchQuery] = useState('');
  const [localFilter, setLocalFilter] = useState('');

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [totalGroups, setTotalGroups] = useState(0);

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState(null);

  const isMobile = useMediaQuery({ query: '(max-width: 768px)' });

  const groupedMedia = useMemo(() => groupMediaByTmdbId(mediaList), [mediaList]);
  const totalPages = Math.ceil(totalGroups / GROUPS_PER_PAGE);

  const filteredData = useMemo(() => {
    if (!localFilter) {
        return groupedMedia;
    }
    return groupedMedia.filter(media => {
        const title = media.tmdb_title || '';
        const overview = media.tmdb_overview || '';
        const genres = media.tmdb_genres || '';
        const regexList = media.torname_regex_list.join(' ');
        const torrentNames = media.torrents.map(t => t.name).join(' ');

        const searchableText = `${title} ${overview} ${genres} ${regexList} ${torrentNames}`.toLowerCase();
        return searchableText.includes(localFilter.toLowerCase());
    });
  }, [groupedMedia, localFilter]);


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
        setError('Failed to fetch media data. Is the backend running?');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchMedia(currentPage);
  }, [currentPage]);

  const handleSearch = () => {
    if (!searchQuery.trim()) {
      fetchMedia(1); // Reload the first page if search is cleared
      return;
    }
    setLoading(true);
    setError(null);
    axios.post(`/api/query`, { torname: searchQuery })
      .then(response => {
        if (currentPage !== 1) {
            setCurrentPage(1);
        } else {
            fetchMedia(1);
        }
      })
      .catch(err => {
        setError(`Search failed: ${err.response?.data?.detail || err.message}`);
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
        setError(`Failed to save media: ${err.response?.data?.detail || err.message}`);
      });
  };

  const handleDeleteMedia = (mediaId) => {
    if (window.confirm('Are you sure you want to delete this media item?')) {
      axios.delete(`/api/media/${mediaId}`)
        .then(() => fetchMedia(currentPage))
        .catch(err => {
          setError(`Failed to delete media: ${err.response?.data?.detail || err.message}`);
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
                  <span className="text-muted small">No Poster</span>
                </div>
              }
            </div>
          ),
          disableSortBy: true, // Disable sorting on poster
          width: 60,
          maxWidth: 70,
          minWidth: 50,
        },
        {
          Header: '媒体详情',
          accessor: 'tmdb_title',
          // Add a second accessor for sorting by year
          sortAccessor: 'tmdb_year',
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
          // No width or minWidth for Details to allow it to expand
        },
      ];

      if (!isMobile) {
        baseColumns.push(
          {
            Header: '正则规则',
            accessor: 'torname_regex_list',
            // Custom sort for number of rules
            sortType: (rowA, rowB) => {
                return rowA.original.torname_regex_list.length > rowB.original.torname_regex_list.length ? 1 : -1;
            },
            Cell: ({ value }) => (
              <ul className="list-unstyled mb-0 small">
                {value.map((regex, index) => (
                  <li key={index}><code style={{ whiteSpace: 'normal' }}>{regex}</code></li>
                ))}
              </ul>
            ),
            width: 50,
          },
          {
            Header: '种子',
            accessor: 'torrents',
            Cell: ({ value }) => value.length,
            sortType: 'basic',
            width: 10,

          }
        );
      }

      baseColumns.push(
        {
          Header: '操作',
          id: 'actions',
          disableSortBy: true, // Disable sorting on actions
          Cell: ({ row }) => (
            <div className="text-center" onClick={(e) => e.stopPropagation()}>
                <Button variant="outline-warning" size="sm" className="me-1" onClick={() => handleOpenModal(row.original.originalItems[0])} title="Edit"><span role="img" aria-label="edit">&#9998;</span></Button>
                <Button variant="outline-danger" size="sm" onClick={() => handleDeleteMedia(row.original.originalItems[0].id)} title="Delete"><span role="img" aria-label="delete">&#128465;</span></Button>
            </div>
          ),
          width: 20,
        }
      );

      return baseColumns;
    },
    [isMobile, handleOpenModal, handleDeleteMedia]
  );

  return (
    <Container fluid className="mt-4" style={{ fontSize: isMobile ? '0.75rem' : '0.875rem' }}>
      <h1 className="mb-4">TMDb Media Manager</h1>
      {error && <Alert variant="danger" onClose={() => setError(null)} dismissible>{error}</Alert>}
      <Row className="mb-3">
        <Col lg={5} md={6} xs={12} className="mb-2 mb-md-0">
          <InputGroup>
            <FormControl
              placeholder="Add media by torrent name..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && handleSearch()}
            />
            <Button variant="primary" onClick={handleSearch}>Add from TMDb</Button>
          </InputGroup>
        </Col>
        <Col lg={4} md={6} xs={12} className="mb-2 mb-md-0">
            <FormControl
              placeholder="Filter loaded items..."
              value={localFilter}
              onChange={e => setLocalFilter(e.target.value)}
            />
        </Col>
        <Col lg={3} xs={12} className="text-lg-end">
          <Button variant="success" onClick={() => handleOpenModal()}>+ Add Manually</Button>
        </Col>
      </Row>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <>
          <Table columns={columns} data={filteredData} onEdit={handleOpenModal} onDelete={handleDeleteMedia} />
          {totalPages > 0 && (
            <Row className="justify-content-center align-items-center mt-3">
              <Col xs="auto" className="text-muted small me-3">
                Page {currentPage} of {totalPages} (Total: {totalGroups} items)
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
  );
}

export default App;
